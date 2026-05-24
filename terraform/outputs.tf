output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.network.public_subnet_ids
}

output "s3_bucket_name" {
  description = "S3 bucket name for logs"
  value       = aws_s3_bucket.logs.id
}

output "ec2_instance_ids" {
  description = "EC2 instance IDs"
  value       = aws_instance.web[*].id
}

output "orphaned_volume_id" {
  description = "Intentionally orphaned EBS volume ID (for Cost Janitor testing)"
  value       = aws_ebs_volume.orphaned.id
}

output "security_group_id" {
  description = "Web security group ID"
  value       = module.network.web_security_group_id
}
