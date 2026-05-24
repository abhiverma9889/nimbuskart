"""
Unit tests for Cost Janitor.
Run with: pytest janitor/tests/test_janitor.py
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import the janitor module
import sys
sys.path.insert(0, "../")

from janitor import CostJanitor


@pytest.fixture
def janitor():
    """Create a test instance without real AWS calls."""
    with patch("janitor.boto3.client"):
        j = CostJanitor(region="us-east-1")
        j.ec2 = Mock()
        j.s3 = Mock()
        j.account_id = "123456789012"
        return j


def test_ebs_orphan_detection(janitor):
    """Test detection of unattached EBS volumes."""
    janitor.ec2.describe_volumes.return_value = {
        "Volumes": [
            {
                "VolumeId": "vol-12345",
                "State": "available",
                "Size": 10,
                "CreateTime": datetime.utcnow() - timedelta(days=21),
                "Tags": [
                    {"Key": "Project", "Value": "nimbuskart"},
                    {"Key": "Environment", "Value": "staging"},
                    {"Key": "Owner", "Value": "team"},
                    {"Key": "ManagedBy", "Value": "terraform"},
                ],
            }
        ]
    }

    janitor.scan_ebs_volumes()
    assert len(janitor.findings) == 1
    assert janitor.findings[0]["resource_type"] == "ebs_volume"
    assert janitor.findings[0]["reason"] == "unattached"
    assert janitor.findings[0]["safe_to_auto_delete"] is True


def test_missing_tags_detection(janitor):
    """Test detection of resources with missing required tags."""
    janitor.ec2.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-12345",
                        "LaunchTime": datetime.utcnow() - timedelta(days=5),
                        "Tags": [
                            {"Key": "Environment", "Value": "dev"},
                        ],
                    }
                ]
            }
        ]
    }

    janitor.scan_missing_tags()
    assert len(janitor.findings) == 1
    assert janitor.findings[0]["reason"] == "missing_tags"
    assert janitor.findings[0]["safe_to_auto_delete"] is False
    assert set(janitor.findings[0]["missing_tags"]) == {"Project", "Owner", "ManagedBy"}


def test_protected_tag_skipped(janitor):
    """Test that Protected=true prevents auto-deletion."""
    janitor.findings = [
        {
            "resource_id": "vol-12345",
            "resource_type": "ebs_volume",
            "safe_to_auto_delete": True,
            "tags": {"Protected": "true"},
        }
    ]

    # Verify _is_protected logic
    tags = [{"Key": "Protected", "Value": "true"}]
    assert janitor._is_protected(tags) is True


def test_report_generation(janitor, tmp_path):
    """Test JSON report generation."""
    janitor.findings = [
        {
            "resource_id": "vol-12345",
            "resource_type": "ebs_volume",
            "reason": "unattached",
            "age_days": 21,
            "estimated_monthly_cost_usd": 8.0,
            "tags": {"Project": "test"},
            "suggested_action": "delete",
            "safe_to_auto_delete": True,
        }
    ]

    output_file = str(tmp_path / "report.json")
    report = janitor.generate_report(output_file=output_file)

    assert report["summary"]["total_orphans"] == 1
    assert report["summary"]["estimated_monthly_waste_usd"] == 8.0

    # Verify file was written
    with open(output_file) as f:
        data = json.load(f)
        assert data["account_id"] == "123456789012"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
