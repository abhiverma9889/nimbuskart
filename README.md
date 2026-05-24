# NimbusKart Cost Hygiene Automation

## Overview

This project automates the detection and remediation of orphaned cloud resources for NimbusKart, an e-commerce startup bleeding money on unattached EBS volumes, stopped instances, and untagged infrastructure. We use Infrastructure as Code (Terraform on LocalStack), automated scanning (Cost Janitor), and CI/CD integration (GitHub Actions) to continuously detect and report wasteful resources without touching a real AWS account.

## How to run locally

```bash
# Clone the repository

cd nimbuskart-cost-automation

# Start LocalStack
docker run --rm -d -p 4566:4566 --name localstack localstack/localstack
sleep 5

# Install Terraform (if not present)
# On macOS: brew install terraform
# On Linux: https://www.terraform.io/downloads.html

# Initialize and apply Terraform
cd terraform
terraform init -backend=false
terraform plan
terraform apply -auto-approve
cd ..

# Install Python dependencies
pip install -r janitor/requirements.txt

# Run Cost Janitor in dry-run mode
python janitor/janitor.py --dry-run

# View the report
cat janitor/report.json
cat janitor/report.md

# To delete orphaned resources (be careful!)
python janitor/janitor.py --delete

# Stop LocalStack
docker stop localstack
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         NimbusKart Infrastructure           │
├─────────────────────────────────────────────┤
│  VPC (10.20.0.0/16)                         │
│  ├── Public Subnet AZ-1 (2 EC2 t3.micro)   │
│  ├── Public Subnet AZ-2                    │
│  ├── S3 Bucket (logs, versioning enabled)  │
│  └── EBS Volume (orphaned, unattached)     │
└─────────────────────────────────────────────┘
           ↓
    ┌──────────────────┐
    │  Cost Janitor    │
    ├──────────────────┤
    │ - Scan AWS       │
    │ - Find orphans   │
    │ - Report findings│
    │ - (Optional) Fix │
    └──────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│      GitHub Actions CI/CD Pipeline          │
├─────────────────────────────────────────────┤
│ 1. Spin up LocalStack                       │
│ 2. Apply Terraform                          │
│ 3. Run Cost Janitor --dry-run               │
│ 4. Upload report.json artifact              │
│ 5. Comment on PR with findings              │
└─────────────────────────────────────────────┘
```

## Decisions & deviations

- **SSH from 0.0.0.0/0**: The spec allows this but it's unsafe. Changed default to require explicit CIDR input via variable; documented why in security comments.
- **No actual deletion by default**: --delete mode requires explicit confirmation; we do not auto-delete without human review, even in CI.
- **Protected tag override**: Any resource tagged `Protected=true` is never deleted, even in --delete mode, to prevent accidental outages.
- **Cost estimates are static**: Real costs vary by region and rate changes; we cite sources and note this is approximate.
- **LocalStack limitations**: DynamoDB, Lambda, and advanced tagging filters are mocked; real solution would use boto3 directly against AWS APIs.

## Trade-offs

With one more week, I would:
1. Add multi-cloud support (GCP/Azure) with pluggable provider modules.
2. Build a web dashboard to visualize trends over time (monthly waste, remediation rate).
3. Add Slack/email notifications from the GitHub Actions workflow.
4. Implement a cost-allocation tagging audit with auto-fix suggestions.
5. Write comprehensive unit and integration tests with pytest.

## AI usage disclosure

- **Claude**: Used for Terraform module boilerplate and Python argparse structure. Caught a subtle bug in cost calculation logic.
- **ChatGPT**: Helped debug a moto mocking issue with EC2 instance state timestamps.
- **What AI got wrong**: Claude initially suggested a complex CloudWatch-based solution; I simplified to local scanning instead (better for an assignment, clearer logic).
- **What I built manually**: The entire cost schema, tagging validation logic, and PR comment formatting. This is the core judgment call — safety and clear reporting matter more than fancy code.

---

**Status**: Fully working | 8 hours spent | LocalStack + Docker required
