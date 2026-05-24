#!/usr/bin/env python3
"""
Cost Janitor: Detects and optionally cleans up orphaned AWS resources.
Designed to run against LocalStack or real AWS; exits with code 1 if orphans found.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3
from botocore.config import Config

from constants import PRICING, REQUIRED_TAGS

# Configure for LocalStack
boto3_config = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    region_name="us-east-1",
)


class CostJanitor:
    def __init__(self, region: str = "us-east-1", endpoint_url: str = None):
        """Initialize with AWS clients."""
        self.region = region
        self.endpoint_url = endpoint_url
        self.account_id = "000000000000"  # Default for LocalStack
        self.findings: List[Dict[str, Any]] = []

        # Create clients
        kwargs = {"config": boto3_config}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        self.ec2 = boto3.client("ec2", region_name=region, **kwargs)
        self.s3 = boto3.client("s3", region_name=region, **kwargs)

        try:
            sts = boto3.client("sts", **kwargs)
            self.account_id = sts.get_caller_identity()["Account"]
        except Exception as e:
            print(f"Warning: Could not fetch account ID: {e}")

    def scan_ebs_volumes(self) -> None:
        """Detect unattached EBS volumes."""
        try:
            response = self.ec2.describe_volumes()
            for volume in response.get("Volumes", []):
                if volume["State"] == "available":
                    self._add_finding(
                        resource_id=volume["VolumeId"],
                        resource_type="ebs_volume",
                        reason="unattached",
                        age_days=self._calculate_age(volume.get("CreateTime")),
                        tags=volume.get("Tags", []),
                        cost=PRICING["ebs_gp3_per_gb_month"] * volume["Size"],
                    )
        except Exception as e:
            print(f"Error scanning EBS volumes: {e}", file=sys.stderr)

    def scan_ec2_instances(self, stopped_days: int = 14) -> None:
        """Detect stopped EC2 instances past retention threshold."""
        try:
            response = self.ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
            )
            for reservation in response.get("Reservations", []):
                for instance in reservation["Instances"]:
                    age = self._calculate_age(instance.get("StateTransitionReason", ""))
                    if age >= stopped_days:
                        self._add_finding(
                            resource_id=instance["InstanceId"],
                            resource_type="ec2_instance",
                            reason=f"stopped_for_{age}_days",
                            age_days=age,
                            tags=instance.get("Tags", []),
                            cost=PRICING["ec2_t3_micro_monthly"],
                        )
        except Exception as e:
            print(f"Error scanning EC2 instances: {e}", file=sys.stderr)

    def scan_elastic_ips(self) -> None:
        """Detect unassociated Elastic IPs."""
        try:
            response = self.ec2.describe_addresses()
            for eip in response.get("Addresses", []):
                if "AssociationId" not in eip:
                    self._add_finding(
                        resource_id=eip["PublicIp"],
                        resource_type="elastic_ip",
                        reason="not_associated",
                        age_days=self._calculate_age(eip.get("AllocationTime")),
                        tags=eip.get("Tags", []),
                        cost=PRICING["elastic_ip_monthly"],
                    )
        except Exception as e:
            print(f"Error scanning Elastic IPs: {e}", file=sys.stderr)

    def scan_missing_tags(self) -> None:
        """Detect resources missing required tags."""
        try:
            response = self.ec2.describe_instances()
            for reservation in response.get("Reservations", []):
                for instance in reservation["Instances"]:
                    missing = self._check_missing_tags(instance.get("Tags", []))
                    if missing:
                        self._add_finding(
                            resource_id=instance["InstanceId"],
                            resource_type="ec2_instance",
                            reason="missing_tags",
                            age_days=self._calculate_age(instance.get("LaunchTime")),
                            tags=instance.get("Tags", []),
                            cost=PRICING["ec2_t3_micro_monthly"],
                            extra_info={"missing_tags": missing},
                        )
        except Exception as e:
            print(f"Error scanning for missing tags: {e}", file=sys.stderr)

    def generate_report(self, output_file: str = "report.json") -> Dict[str, Any]:
        """Generate JSON report."""
        total_cost = sum(f.get("estimated_monthly_cost_usd", 0) for f in self.findings)

        report = {
            "scan_timestamp": datetime.utcnow().isoformat() + "Z",
            "account_id": self.account_id,
            "region": self.region,
            "summary": {
                "total_orphans": len(self.findings),
                "estimated_monthly_waste_usd": round(total_cost, 2),
            },
            "findings": self.findings,
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return report

    def generate_markdown_summary(self, output_file: str = "report.md") -> str:
        """Generate human-readable Markdown summary."""
        total_cost = sum(f.get("estimated_monthly_cost_usd", 0) for f in self.findings)

        md = f"""# Cost Janitor Report

**Generated**: {datetime.utcnow().isoformat()}Z  
**Account**: {self.account_id}  
**Region**: {self.region}

## Summary

- **Total orphans found**: {len(self.findings)}
- **Estimated monthly waste**: ${total_cost:.2f}

## Findings

"""
        for finding in self.findings:
            md += f"""### {finding['resource_id']} ({finding['resource_type']})
- **Reason**: {finding['reason']}
- **Age**: {finding['age_days']} days
- **Estimated cost**: ${finding['estimated_monthly_cost_usd']:.2f}/month
- **Safe to delete**: {finding['safe_to_auto_delete']}

"""

        with open(output_file, "w") as f:
            f.write(md)

        return md

    def delete_resources(self, dry_run: bool = True) -> None:
        """Delete orphaned resources (respects Protected tag)."""
        for finding in self.findings:
            if not finding["safe_to_auto_delete"]:
                print(f"Skipping {finding['resource_id']} (not safe to auto-delete)")
                continue

            if self._is_protected(finding["tags"]):
                print(f"Skipping {finding['resource_id']} (Protected=true)")
                continue

            resource_id = finding["resource_id"]
            resource_type = finding["resource_type"]

            try:
                if resource_type == "ebs_volume":
                    self.ec2.delete_volume(VolumeId=resource_id, DryRun=dry_run)
                    print(f"Deleted EBS volume {resource_id}")
                elif resource_type == "elastic_ip":
                    self.ec2.release_address(PublicIp=resource_id, DryRun=dry_run)
                    print(f"Released Elastic IP {resource_id}")
            except Exception as e:
                print(f"Error deleting {resource_id}: {e}", file=sys.stderr)

    def _add_finding(
        self,
        resource_id: str,
        resource_type: str,
        reason: str,
        age_days: int,
        tags: List[Dict],
        cost: float,
        extra_info: Dict = None,
    ) -> None:
        """Add a finding to the report."""
        tag_dict = {tag["Key"]: tag.get("Value") for tag in tags}
        missing = self._check_missing_tags(tags)

        finding = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "reason": reason,
            "age_days": age_days,
            "estimated_monthly_cost_usd": round(cost, 2),
            "tags": tag_dict,
            "suggested_action": "delete" if not missing else "review",
            "safe_to_auto_delete": not missing,
        }

        if extra_info:
            finding.update(extra_info)

        self.findings.append(finding)

    def _calculate_age(self, date_obj: Any) -> int:
        """Calculate age in days."""
        if not date_obj:
            return 0
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.fromisoformat(date_obj.replace("Z", "+00:00"))
            except Exception:
                return 0
        if hasattr(date_obj, "timestamp"):
            days = (datetime.utcnow() - date_obj).days
            return max(days, 0)
        return 0

    def _check_missing_tags(self, tags: List[Dict]) -> List[str]:
        """Check for missing required tags."""
        tag_dict = {tag["Key"]: tag.get("Value") for tag in tags}
        return [t for t in REQUIRED_TAGS if not tag_dict.get(t)]

    def _is_protected(self, tags: List[Dict]) -> bool:
        """Check if resource has Protected=true tag."""
        tag_dict = {tag["Key"]: tag.get("Value") for tag in tags}
        return tag_dict.get("Protected") == "true"


def main():
    parser = argparse.ArgumentParser(
        description="Cost Janitor: Find and clean up orphaned AWS resources"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )
    parser.add_argument(
        "--endpoint-url",
        help="LocalStack endpoint URL (e.g., http://localhost:4566)",
    )
    parser.add_argument(
        "--stopped-days",
        type=int,
        default=14,
        help="Days threshold for stopped instances (default: 14)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report only, do not delete (default)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete orphaned resources (skips Protected=true)",
    )

    args = parser.parse_args()

    # Initialize janitor
    janitor = CostJanitor(
        region=args.region,
        endpoint_url=args.endpoint_url,
    )

    # Scan
    print("Scanning for orphaned resources...")
    janitor.scan_ebs_volumes()
    janitor.scan_ec2_instances(stopped_days=args.stopped_days)
    janitor.scan_elastic_ips()
    janitor.scan_missing_tags()

    # Generate reports
    report = janitor.generate_report()
    janitor.generate_markdown_summary()

    print(f"Found {len(janitor.findings)} orphaned resources")
    print(f"Estimated waste: ${report['summary']['estimated_monthly_waste_usd']:.2f}/month")

    # Delete if requested
    if args.delete:
        print("\nDeleting resources...")
        janitor.delete_resources(dry_run=False)

    # Exit with error code if orphans found in dry-run mode
    if args.dry_run and len(janitor.findings) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
