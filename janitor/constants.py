"""
Cost Janitor pricing constants.

Sources:
- EBS GP3: https://aws.amazon.com/ebs/pricing/ (us-east-1, $0.08/GB-month for 3,000 IOPS)
- EC2 t3.micro: https://aws.amazon.com/ec2/pricing/on-demand/ (us-east-1, ~$0.0104/hour)
- Elastic IP: https://aws.amazon.com/ec2/pricing/on-demand/ (us-east-1, $0.005/hour when associated, free when not)

These are approximate and regional. Production systems should fetch pricing from AWS Pricing API.
"""

PRICING = {
    "ebs_gp3_per_gb_month": 0.08,  # $/GB/month for standard gp3
    "ec2_t3_micro_monthly": 7.50,  # ~730 hours * $0.0104/hour (us-east-1)
    "elastic_ip_monthly": 3.65,    # $0.005/hour * 730 hours (unused EIP charges hourly)
}

REQUIRED_TAGS = [
    "Project",
    "Environment",
    "Owner",
    "ManagedBy",
]
