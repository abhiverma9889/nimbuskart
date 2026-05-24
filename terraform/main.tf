terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # LocalStack configuration
  access_key                  = "testing"
  secret_key                  = "testing"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2 = "http://localhost:4566"
    s3  = "http://localhost:4566"
  }
}

module "network" {
  source = "./modules/network"

  project_name = var.project_name
  environment  = var.environment
  owner        = var.owner
  vpc_cidr     = var.vpc_cidr
  ssh_cidr     = var.ssh_cidr
}

# EC2 Instances (Web Tier)
resource "aws_instance" "web" {
  count                = 2
  ami                  = "ami-12c6146b" # LocalStack default AMI ID
  instance_type        = var.instance_type
  subnet_id            = module.network.public_subnet_ids[count.index]
  security_groups      = [module.network.web_security_group_id]
  iam_instance_profile = aws_iam_instance_profile.nimbuskart_profile.name

  tags = {
    Name        = "nimbuskart-web-${count.index + 1}"
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
    Tier        = "web"
  }
}

# Orphaned EBS Volume (intentional, for Cost Janitor to find)
resource "aws_ebs_volume" "orphaned" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = 10
  type              = "gp3"
  encrypted         = false

  tags = {
    Name        = "orphaned-volume-demo"
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
}

# S3 Bucket for logs
resource "aws_s3_bucket" "logs" {
  bucket = "nimbuskart-logs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "nimbuskart-logs"
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# IAM Role for EC2 instances
resource "aws_iam_role" "nimbuskart_role" {
  name = "nimbuskart-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "nimbuskart-role"
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_instance_profile" "nimbuskart_profile" {
  name = "nimbuskart-profile"
  role = aws_iam_role.nimbuskart_role.name
}

# Data sources
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}
