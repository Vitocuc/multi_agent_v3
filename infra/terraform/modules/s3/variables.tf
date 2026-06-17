variable "project_name" {
  description = "Project identifier used in resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
}

variable "kms_key_id" {
  description = "ARN of a KMS key for SSE-KMS encryption. Leave empty for SSE-S3 (AES256)."
  type        = string
  default     = ""
}

variable "force_destroy" {
  description = "Allow Terraform to destroy the bucket even if non-empty. Set false in prod."
  type        = bool
  default     = false
}
