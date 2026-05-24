# Quick Reference

## Useful commands

```bash
# Start LocalStack
docker run --rm -d -p 4566:4566 --name localstack localstack/localstack

# Stop LocalStack
docker stop localstack

# Test Terraform
cd terraform
terraform init -backend=false
terraform validate
terraform fmt
terraform plan
terraform apply -auto-approve
terraform destroy -auto-approve

# Test Janitor
cd janitor
python janitor.py --region us-east-1 --endpoint-url http://localhost:4566 --dry-run
python janitor.py --region us-east-1 --endpoint-url http://localhost:4566 --delete

# View reports
jq . janitor/report.json
cat janitor/report.md

# Run tests
pytest janitor/tests/ -v

# Check formatting
terraform fmt -recursive
black janitor/*.py
```

## File structure quick lookup

| File | Purpose |
|------|---------|
| README.md | Project overview, how to run |
| SUBMISSION.md | Submission checklist, candidate info |
| DESIGN.md | Multi-cloud design, IAM, safety nets, observability |
| terraform/main.tf | VPC, EC2, S3, orphaned volume |
| terraform/modules/network/ | Reusable network module |
| janitor/janitor.py | Main cost detection script |
| janitor/constants.py | Pricing and tag constants |
| .github/workflows/cost-janitor.yml | CI/CD pipeline |

## Debugging tips

### LocalStack won't start
```bash
docker logs localstack
# Check port 4566 is free: lsof -i :4566
```

### Terraform apply fails
```bash
# Check LocalStack is running
curl http://localhost:4566/_localstack/health

# Set debug output
TF_LOG=DEBUG terraform apply -auto-approve
```

### Janitor finds no resources
```bash
# Verify Terraform created resources
aws --endpoint-url http://localhost:4566 ec2 describe-instances --region us-east-1

# Verify boto3 can reach LocalStack
python -c "import boto3; client = boto3.client('ec2', endpoint_url='http://localhost:4566'); print(client.describe_instances())"
```

### GitHub Actions workflow fails
Check the workflow logs in Actions tab:
1. Does LocalStack service start? (check health endpoint)
2. Does Terraform init/apply succeed?
3. Is the janitor report generated?
4. Are artifacts uploaded?

---

## Next steps after submission

1. Record a 5-minute walkthrough video (see docs/walkthrough.md)
2. Fill in SUBMISSION.md with candidate info and video link
3. Push to GitHub as a public repository
4. Reply to recruiter with repo URL and video link
