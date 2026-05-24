# Walkthrough Guide

This document outlines what to cover in your 5-minute walkthrough video.

## Part 1: Start LocalStack and apply Terraform (1 min)

1. Open terminal, show the project structure:
   ```bash
   tree nimbuskart-assignment
   ```

2. Start LocalStack:
   ```bash
   docker run --rm -d -p 4566:4566 --name localstack localstack/localstack
   sleep 5
   curl http://localhost:4566/_localstack/health
   ```

3. Navigate to terraform directory:
   ```bash
   cd terraform
   terraform init -backend=false
   terraform validate
   terraform fmt -check
   terraform apply -auto-approve
   ```

4. Show the resources created:
   ```bash
   terraform output
   ```

## Part 2: Run Cost Janitor and walk through findings (2 min)

1. Navigate to janitor directory:
   ```bash
   cd ../janitor
   pip install -r requirements.txt
   ```

2. Run in dry-run mode:
   ```bash
   python janitor.py --region us-east-1 --endpoint-url http://localhost:4566 --dry-run
   ```

3. Show the JSON report:
   ```bash
   cat report.json | jq .
   ```

4. Show the Markdown summary:
   ```bash
   cat report.md
   ```

5. **Walk through one finding**: Pick the orphaned EBS volume (vol-xxx) and explain:
   - Why it was detected (unattached state)
   - Age calculation
   - Cost estimate
   - Why it's safe to delete (has all required tags)

## Part 3: Design decision you're proud of (1 min)

Pick one of:
- **Modular Terraform**: Show the network module and explain why splitting into modules matters for multi-cloud.
- **Provider abstraction**: Describe the adapter pattern in DESIGN.md and why it enables GCP/Azure.
- **Safety guardrails**: Explain the Protected=true tag and why blindly auto-deleting is dangerous.
- **Report schema**: Show report.json and explain why the "safe_to_auto_delete" field prevents accidents.

## Part 4: One thing you'd change (30 sec)

Examples:
- "I'd add Slack notifications from GitHub Actions so the team sees findings immediately."
- "I'd implement multi-account scanning with a central dashboard."
- "I'd fetch real pricing from AWS Pricing API instead of hardcoding."

---

## Recording checklist

- [ ] Microphone works, no background noise
- [ ] Terminal text is readable (font size ≥ 16pt)
- [ ] Internet connection stable (no cuts)
- [ ] Screen capture at native resolution or 1080p
- [ ] Total time ≤ 5 minutes
- [ ] No pauses > 10 seconds

Upload to Loom (free, no account needed) or YouTube unlisted, and paste the link in SUBMISSION.md.
