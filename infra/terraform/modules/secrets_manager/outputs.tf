output "kms_key_arn" {
  description = "ARN of the KMS key used to encrypt all Secrets Manager secrets."
  value       = aws_kms_key.secrets.arn
}

output "kms_key_id" {
  description = "ID of the KMS key used to encrypt all Secrets Manager secrets."
  value       = aws_kms_key.secrets.key_id
}

output "db_url_secret_arn" {
  description = "ARN of the DB_URL secret in Secrets Manager."
  value       = aws_secretsmanager_secret.db_url.arn
}

output "db_url_secret_name" {
  description = "Name of the DB_URL secret in Secrets Manager."
  value       = aws_secretsmanager_secret.db_url.name
}

output "redis_url_secret_arn" {
  description = "ARN of the REDIS_URL secret in Secrets Manager."
  value       = aws_secretsmanager_secret.redis_url.arn
}

output "redis_url_secret_name" {
  description = "Name of the REDIS_URL secret in Secrets Manager."
  value       = aws_secretsmanager_secret.redis_url.name
}

output "jwt_secret_arn" {
  description = "ARN of the JWT_SECRET in Secrets Manager."
  value       = aws_secretsmanager_secret.jwt_secret.arn
}

output "jwt_secret_name" {
  description = "Name of the JWT_SECRET in Secrets Manager."
  value       = aws_secretsmanager_secret.jwt_secret.name
}

output "webhook_hmac_secret_arn" {
  description = "ARN of the WEBHOOK_HMAC_SECRET in Secrets Manager."
  value       = aws_secretsmanager_secret.webhook_hmac_secret.arn
}

output "webhook_hmac_secret_name" {
  description = "Name of the WEBHOOK_HMAC_SECRET in Secrets Manager."
  value       = aws_secretsmanager_secret.webhook_hmac_secret.name
}

output "read_secrets_policy_arn" {
  description = "ARN of the IAM policy granting read access to application secrets."
  value       = aws_iam_policy.read_app_secrets.arn
}
