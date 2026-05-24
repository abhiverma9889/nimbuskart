# Cost Janitor Report

**Generated**: 2026-01-15T10:00:00Z  
**Account**: 000000000000  
**Region**: us-east-1

## Summary

- **Total orphans found**: 3
- **Estimated monthly waste**: $19.27

## Findings

### vol-12345 (ebs_volume)
- **Reason**: unattached
- **Age**: 21 days
- **Estimated cost**: $8.00/month
- **Safe to delete**: true
- **Tags**: Project=nimbuskart, Environment=staging, Owner=platform-team, ManagedBy=terraform

### i-67890 (ec2_instance)
- **Reason**: stopped_for_30_days
- **Age**: 30 days
- **Estimated cost**: $7.50/month
- **Safe to delete**: false
- **Missing tags**: Project, Owner, ManagedBy
- **Action**: Review before deletion — missing required tags

### 52.1.2.3 (elastic_ip)
- **Reason**: not_associated
- **Age**: 45 days
- **Estimated cost**: $3.77/month
- **Safe to delete**: true
- **Tags**: Project=nimbuskart, Environment=staging, Owner=platform-team, ManagedBy=terraform

---

## Next steps

1. Review findings marked "Safe to delete: false" for false positives.
2. Add missing tags to resources that should be kept.
3. To delete safe resources, run: `python janitor/janitor.py --delete --endpoint-url http://localhost:4566`
