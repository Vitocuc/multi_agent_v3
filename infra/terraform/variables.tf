# =============================================================================
# Global Variables
# =============================================================================
# All secret values are sourced from AWS Secrets Manager at runtime.
# No secret values appear in this file or in terraform.tfvars.
# Workspace-specific values are supplied via env/<workspace>.tfvars files
# which are gitignored.
# =============================================================================

variable "aws_region" {
  description = "AWS region for all resources — must be eu-central-1 per doc1 security contract."
  type        = string
  default     = "eu-central-1"

  validation {
    condition     = var.aws_region == "eu-central-1"
    error_message = "All resources must be deployed in eu-central-1 (EU/EEA) per the security contract."
  }
}

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project identifier used in resource naming."
  type        = string
  default     = "protegopay"
}

# ---------------------------------------------------------------------------
# VPC / Networking
# ---------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use for subnet placement (min 2 for RDS Multi-AZ)."
  type        = list(string)
  default     = ["eu-central-1a", "eu-central-1b", "eu-central-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (NAT Gateway, ALB)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (RDS, Redis, application)."
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL
# ---------------------------------------------------------------------------

variable "rds_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS in GiB."
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "Maximum storage autoscaling cap in GiB."
  type        = number
  default     = 100
}

variable "rds_database_name" {
  description = "Initial database name."
  type        = string
  default     = "protegopay"
}

variable "rds_backup_retention_days" {
  description = "Number of days to retain automated RDS backups."
  type        = number
  default     = 7
}

variable "rds_deletion_protection" {
  description = "Enable deletion protection on RDS. Should be true for prod."
  type        = bool
  default     = false
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ deployment for RDS. Should be true for staging and prod."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# ElastiCache Redis
# ---------------------------------------------------------------------------

variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_clusters" {
  description = "Number of cache clusters (nodes) in the replication group."
  type        = number
  default     = 1
}

variable "redis_engine_version" {
  description = "Redis engine version."
  type        = string
  default     = "7.1"
}

variable "redis_port" {
  description = "Redis port."
  type        = number
  default     = 6379
}

# ---------------------------------------------------------------------------
# S3 GDPR Export Bucket
# ---------------------------------------------------------------------------

variable "s3_gdpr_force_destroy" {
  description = "Allow Terraform to destroy the S3 bucket even if it contains objects. Set to false in prod."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Secrets Manager
# ---------------------------------------------------------------------------

variable "secrets_recovery_window_days" {
  description = "Number of days before a deleted secret is permanently deleted (0 = immediate)."
  type        = number
  default     = 7
}
