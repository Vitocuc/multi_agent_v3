# Terraform remote state backend
# State is stored in S3 with versioning enabled and DynamoDB state locking.
# Never commit .tfstate files — they are managed exclusively by this backend.
#
# Prerequisites (one-time manual bootstrap per AWS account):
#   1. Create S3 bucket: protegopay-terraform-state-<account_id>
#      with versioning enabled, server-side encryption (AES-256), and
#      public-access block fully enabled.
#   2. Create DynamoDB table: protegopay-terraform-locks
#      with partition key: LockID (String)
#   3. Run: terraform init -backend-config="env/<workspace>.backend.hcl"
#
# The bucket name and region are parameterised via workspace-specific
# backend config files so the same modules serve dev/staging/prod without
# cross-environment state contamination.

terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    # These values are supplied at `terraform init` time via -backend-config
    # to avoid hardcoding account-specific values here.
    # Example:
    #   terraform init \
    #     -backend-config="bucket=protegopay-terraform-state-<account_id>" \
    #     -backend-config="key=protegopay/<workspace>/terraform.tfstate" \
    #     -backend-config="region=eu-central-1" \
    #     -backend-config="dynamodb_table=protegopay-terraform-locks" \
    #     -backend-config="encrypt=true"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "protegopay"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
