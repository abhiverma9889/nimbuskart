# Submission — DevOps Engineer Assignment



## Deliverables checklist

- [ ] Part A: Terraform code under /terraform applies cleanly on LocalStack
- [ ] Part A: `terraform validate` and `terraform fmt -check` both pass
- [ ] Part B: Janitor script runs in --dry-run mode and produces report.json
- [ ] Part B: GitHub Actions workflow runs green on a fresh PR
- [ ] Part B: --delete mode respects Protected=true tag
- [ ] Part C: DESIGN.md is present and within 2 pages
- [ ] Walkthrough video link below is accessible (unlisted is fine)


## Known limitations

- LocalStack does not fully emulate all AWS tag filtering APIs; real implementation would use boto3 directly.
- Cost estimates are hardcoded; a production system would fetch real pricing from AWS Pricing API.
- No support for cross-account scanning; each region/account requires a separate run.
- Terraform does not test against actual IAM policies; review DESIGN.md for recommended permissions.

## AI usage disclosure

- **Claude**: Terraform module structure, Python argparse scaffolding
- **ChatGPT**: Debugged moto EC2 state timestamp issue
- **What went wrong**: Initial suggestion for CloudWatch-based solution was over-engineered; switched to local scanning
- **Manual sections**: Tagging validation logic, cost schema, report formatting — these are the core safety decisions

---

*Ready to submit? Replace placeholders above, add video link, and send to recruiter.*
