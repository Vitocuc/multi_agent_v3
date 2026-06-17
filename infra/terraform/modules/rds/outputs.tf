output "db_instance_id" {
  description = "ID of the RDS instance."
  value       = aws_db_instance.main.id
}

output "db_instance_arn" {
  description = "ARN of the RDS instance."
  value       = aws_db_instance.main.arn
}

output "db_endpoint" {
  description = "Connection endpoint for the RDS instance (hostname:port)."
  value       = aws_db_instance.main.endpoint
  # Note: This is the hostname only — no credentials included.
}

output "db_name" {
  description = "Name of the default database."
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "Master username for the RDS instance."
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_password" {
  description = "Master password — stored in Secrets Manager after provisioning. Do not use directly."
  value       = random_password.rds_master.result
  sensitive   = true # Marked sensitive so it does not appear in plan/apply output
}

output "security_group_id" {
  description = "ID of the RDS security group."
  value       = aws_security_group.rds.id
}

output "storage_encrypted" {
  description = "Whether storage encryption is enabled (always true)."
  value       = aws_db_instance.main.storage_encrypted
}

output "kms_key_id" {
  description = "KMS key ARN used for RDS encryption at rest."
  value       = aws_db_instance.main.kms_key_id
}
