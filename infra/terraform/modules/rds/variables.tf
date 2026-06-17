variable "project_name" {
  description = "Project identifier used in resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the RDS instance will be created."
  type        = string
}

variable "vpc_cidr_block" {
  description = "VPC CIDR block for security group ingress rules."
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the RDS subnet group."
  type        = list(string)
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage for RDS in GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Maximum storage autoscaling cap in GiB."
  type        = number
  default     = 100
}

variable "database_name" {
  description = "Initial database name."
  type        = string
  default     = "protegopay"
}

variable "backup_retention_days" {
  description = "Number of days to retain automated backups."
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Enable deletion protection. Must be true for prod."
  type        = bool
  default     = false
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment."
  type        = bool
  default     = false
}

variable "kms_key_id" {
  description = "ARN of a customer-managed KMS key for encryption at rest. Leave empty to use AWS managed key."
  type        = string
  default     = ""
}
