output "replication_group_id" {
  description = "ID of the ElastiCache replication group."
  value       = aws_elasticache_replication_group.main.id
}

output "replication_group_arn" {
  description = "ARN of the ElastiCache replication group."
  value       = aws_elasticache_replication_group.main.arn
}

output "primary_endpoint_address" {
  description = "Primary endpoint address for the Redis cluster."
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  # Note: No credentials included. Auth token is in Secrets Manager.
}

output "reader_endpoint_address" {
  description = "Reader endpoint address for the Redis cluster."
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "port" {
  description = "Redis port number."
  value       = aws_elasticache_replication_group.main.port
}

output "auth_token" {
  description = "Redis auth token — stored in Secrets Manager. Do not use directly."
  value       = random_password.redis_auth_token.result
  sensitive   = true # Never appears in plan or apply output
}

output "security_group_id" {
  description = "ID of the Redis security group."
  value       = aws_security_group.redis.id
}

output "at_rest_encryption_enabled" {
  description = "Whether at-rest encryption is enabled (always true)."
  value       = aws_elasticache_replication_group.main.at_rest_encryption_enabled
}
