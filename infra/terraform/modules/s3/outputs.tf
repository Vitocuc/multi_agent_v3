output "gdpr_exports_bucket_id" {
  description = "Name (ID) of the GDPR exports S3 bucket."
  value       = aws_s3_bucket.gdpr_exports.id
}

output "gdpr_exports_bucket_arn" {
  description = "ARN of the GDPR exports S3 bucket."
  value       = aws_s3_bucket.gdpr_exports.arn
}

output "gdpr_exports_bucket_domain_name" {
  description = "Domain name of the GDPR exports S3 bucket (for pre-signed URL generation)."
  value       = aws_s3_bucket.gdpr_exports.bucket_domain_name
}

output "access_logs_bucket_id" {
  description = "Name (ID) of the S3 access logs bucket."
  value       = aws_s3_bucket.access_logs.id
}

output "public_access_block_enabled" {
  description = "Confirmation that all public access block settings are enabled."
  value = {
    block_public_acls       = aws_s3_bucket_public_access_block.gdpr_exports.block_public_acls
    block_public_policy     = aws_s3_bucket_public_access_block.gdpr_exports.block_public_policy
    ignore_public_acls      = aws_s3_bucket_public_access_block.gdpr_exports.ignore_public_acls
    restrict_public_buckets = aws_s3_bucket_public_access_block.gdpr_exports.restrict_public_buckets
  }
}
