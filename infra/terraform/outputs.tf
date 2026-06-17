# =============================================================================
# Root Outputs — ProtegoPay Infrastructure
# =============================================================================
# IMPORTANT: No secret values are output here.
# All sensitive values are marked sensitive = true and stored in Secrets Manager.
# Resource ARNs and endpoint hostnames (not credentials) are documented for
# operators. See infra/README.md for the full resource inventory.
# =============================================================================

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------

output "vpc_id" {
  description = "VPC ID."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs."
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs."
  value       = module.vpc.private_subnet_ids
}

# ---------------------------------------------------------------------------
# RDS
# ---------------------------------------------------------------------------

output "rds_instance_arn" {
  description = "ARN of the RDS PostgreSQL instance."
  value       = module.rds.db_instance_arn
}

output "rds_endpoint" {
  description = "RDS endpoint hostname (no credentials)."
  value       = module.rds.db_endpoint
}

output "rds_storage_encrypted" {
  description = "Whether RDS storage encryption is enabled. Should always be true."
  value       = module.rds.storage_encrypted
}

output "rds_kms_key_id" {
  description = "KMS key ARN used for RDS encryption at rest."
  value       = module.rds.kms_key_id
}

# ---------------------------------------------------------------------------
# ElastiCache Redis
# ---------------------------------------------------------------------------

output "redis_replication_group_arn" {
  description = "ARN of the ElastiCache replication group."
  value       = module.elasticache.replication_group_arn
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint hostname (no credentials)."
  value       = module.elasticache.primary_endpoint_address
}

output "redis_at_rest_encryption_enabled" {
  description = "Whether Redis at-rest encryption is enabled. Should always be true."
  value       = module.elasticache.at_rest_encryption_enabled
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

output "gdpr_exports_bucket_arn" {
  description = "ARN of the GDPR exports S3 bucket."
  value       = module.s3.gdpr_exports_bucket_arn
}

output "gdpr_exports_bucket_id" {
  description = "Name of the GDPR exports S3 bucket."
  value       = module.s3.gdpr_exports_bucket_id
}

output "s3_public_access_block" {
  description = "Public access block configuration (all should be true)."
  value       = module.s3.public_access_block_enabled
}

# ---------------------------------------------------------------------------
# Secrets Manager
# ---------------------------------------------------------------------------

output "secrets_kms_key_arn" {
  description = "ARN of the KMS key used to encrypt Secrets Manager secrets."
  value       = module.secrets_manager.kms_key_arn
}

output "db_url_secret_arn" {
  description = "ARN of the DB_URL secret in Secrets Manager."
  value       = module.secrets_manager.db_url_secret_arn
}

output "redis_url_secret_arn" {
  description = "ARN of the REDIS_URL secret in Secrets Manager."
  value       = module.secrets_manager.redis_url_secret_arn
}

output "jwt_secret_arn" {
  description = "ARN of the JWT_SECRET in Secrets Manager."
  value       = module.secrets_manager.jwt_secret_arn
}

output "webhook_hmac_secret_arn" {
  description = "ARN of the WEBHOOK_HMAC_SECRET in Secrets Manager."
  value       = module.secrets_manager.webhook_hmac_secret_arn
}
