# Design: Multi-Cloud Cost Janitor

## 1. Multi-cloud architecture

To support AWS, GCP, and Azure without rewriting the core, split the Janitor into a provider-agnostic engine and pluggable cloud adapters.

```
CostJanitor (core)
├── Provider Interface (abstract base)
│   ├── scan_orphaned_volumes()
│   ├── scan_orphaned_instances()
│   ├── scan_orphaned_ips()
│   └── scan_missing_tags()
├── AWS Adapter (provider/aws_adapter.py)
├── GCP Adapter (provider/gcp_adapter.py)
└── Azure Adapter (provider/azure_adapter.py)
```

Each adapter implements the interface, translating cloud-specific APIs to a common schema. The core engine orchestrates scans, aggregates findings, and generates reports.

**Benefits**: Adding GCP next quarter means writing a single `GcpAdapter` class (~200 lines), not rewriting the entire janitor.

## 2. IAM permissions

### Read-only mode (--dry-run)

Minimal policy for scanning without destructive access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "ec2:DescribeTags",
        "s3:ListAllMyBuckets",
        "s3:GetBucketVersioning",
        "s3:GetBucketTagging",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### Delete mode (--delete)

Add destructive actions *with account restrictions*:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "ec2:DescribeTags",
        "ec2:DeleteVolume",
        "ec2:ReleaseAddress",
        "ec2:TerminateInstances"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": [
        "ec2:DeleteVolume",
        "ec2:ReleaseAddress",
        "ec2:TerminateInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": [
            "us-east-1-prod",
            "eu-west-1-prod"
          ]
        }
      }
    }
  ]
}
```

This allows deletion in staging but denies it in production regions. Enforce region-based guardrails at policy level, not code level.

## 3. Safety nets for auto-deletion

### Failure mode 1: Silent termination of active workloads
**Problem**: A developer forgot to tag a prod database snapshot. The Janitor sees "untagged EBS volume" and deletes it.  
**Guardrail**:
- *Explicit tag whitelist*: Only delete resources tagged with a known "Cleanup=yes" flag, not the inverse.
- *Age threshold*: Do not delete anything created in the last 7 days (assume recent = in-use).
- *Dry-run-first CI gate*: Make --dry-run mandatory in CI; require manual approval before --delete runs in prod.

### Failure mode 2: Cascade failure from Elastic IP deletion
**Problem**: Deleting an EIP attached to a load balancer's NAT instance breaks all outbound traffic.  
**Guardrail**:
- *Dependency audit*: Before deleting any IP, query ENI attachments and security group references.
- *Protected tag enforcement*: Default to Protected=true on resources in production; require explicit override.
- *Notification gate*: Post a Slack message with a 24-hour hold before deletion in any prod account; require sign-off.

**Implementation**:
```python
def safe_delete_eip(eip_id: str, dry_run: bool = True) -> bool:
    # Check if EIP is in use
    if eip_has_dependencies(eip_id):
        log_alert(f"EIP {eip_id} has dependencies; skipping")
        return False
    
    # Check Protection tag
    if is_protected(eip_id):
        log_alert(f"EIP {eip_id} is Protected=true; skipping")
        return False
    
    # Check age
    if age_days(eip_id) < 7:
        log_alert(f"EIP {eip_id} is < 7 days old; skipping")
        return False
    
    # All checks pass; delete
    ec2.release_address(AllocationId=eip_id, DryRun=dry_run)
    return True
```

## 4. Observability & alerting

Publish these metrics to CloudWatch or Prometheus:

| Metric | Source | Threshold | Action |
|--------|--------|-----------|--------|
| `janitor.orphans_found_count` | Janitor script stdout | > 10 per scan | Alert: unexpected spike in orphans |
| `janitor.estimated_monthly_waste_usd` | report.json summary | > $500 | Alert: cost leakage growing |
| `janitor.deletion_success_rate` | Janitor logs | < 90% | Alert: deletions failing silently |
| `janitor.scan_duration_seconds` | Janitor runtime | > 300 | Alert: API throttling or network issues |
| `janitor.last_successful_scan` | Janitor exit code | > 24 hours ago | Alert: job failing to run |

**Implementation**:
```bash
# In GitHub Actions after scan
aws cloudwatch put-metric-data \
  --namespace "CostJanitor" \
  --metric-name "OrphansFound" \
  --value $(jq '.summary.total_orphans' janitor/report.json)
```

## 5. What we did not build

- **Multi-account orchestration**: This design handles one account at a time. Production needs a coordinator service that runs the Janitor in each AWS account (via cross-account roles) and aggregates findings into a central dashboard.
- **Custom tagging policies per team**: NimbusKart may have different tag requirements per service (some require CostCenter, others require Environment). We hardcoded a fixed tag set; real system needs a YAML policy file per team.
- **Rollback mechanism**: If deletion causes an outage, there is no automatic recovery. Add CloudTrail event streaming to SNS so ops can trigger a restore-from-snapshot automation.
- **Cost forecasting**: We only report current orphans; we don't predict which resources are *about to become* orphaned (e.g., dev instances with no traffic for 3 days). Machine learning on CloudWatch metrics could improve this.
- **Integrations with ticketing**: We post to GitHub PRs. Real system would create/resolve Jira tickets for each finding so FinOps team can track remediation.

---

**Scope decision**: We prioritized a clean, auditable first pass that runs locally and passes human review, over feature completeness. Each item above is a 1–2 week feature lift for a real product.
