# =============================================================================
# S3 Module — GDPR Export Storage — ProtegoPay
# =============================================================================
# Creates an S3 bucket for GDPR Subject Access Request exports with:
# - All public access blocked (no public read or write)
# - Server-side encryption (SSE-S3 AES-256 or SSE-KMS)
# - Versioning enabled
# - Object lifecycle policy (7-day expiry for GDPR exports, 30-day for reports)
# - Access logging
# - Bucket policies denying non-TLS access
# =============================================================================

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# S3 Bucket — GDPR Exports
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "gdpr_exports" {
  bucket        = "${var.project_name}-${var.environment}-gdpr-exports-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.force_destroy

  tags = {
    Name        = "${var.project_name}-${var.environment}-gdpr-exports"
    DataClass   = "sensitive"
    Regulation  = "GDPR"
  }
}

# ---------------------------------------------------------------------------
# Block ALL public access — REQUIRED by security contract
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_public_access_block" "gdpr_exports" {
  bucket = aws_s3_bucket.gdpr_exports.id

  block_public_acls       = true  # Block new public ACLs
  block_public_policy     = true  # Block new public bucket policies
  ignore_public_acls      = true  # Ignore existing public ACLs
  restrict_public_buckets = true  # Restrict public bucket policies
}

# ---------------------------------------------------------------------------
# Versioning — REQUIRED by security contract
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_versioning" "gdpr_exports" {
  bucket = aws_s3_bucket.gdpr_exports.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ---------------------------------------------------------------------------
# Server-Side Encryption — SSE-S3 (AES-256) default
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_server_side_encryption_configuration" "gdpr_exports" {
  bucket = aws_s3_bucket.gdpr_exports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != "" ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id != "" ? var.kms_key_id : null
    }
    bucket_key_enabled = var.kms_key_id != "" ? true : false
  }
}

# ---------------------------------------------------------------------------
# Lifecycle Policy — auto-expire GDPR export objects
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_lifecycle_configuration" "gdpr_exports" {
  bucket = aws_s3_bucket.gdpr_exports.id

  rule {
    id     = "gdpr-sar-expiry"
    status = "Enabled"

    filter {
      prefix = "sar/"
    }

    expiration {
      days = 7 # GDPR SAR export objects expire after 7 days (doc1)
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }

  rule {
    id     = "investor-reports-expiry"
    status = "Enabled"

    filter {
      prefix = "reports/"
    }

    expiration {
      days = 30 # Investor report objects expire after 30 days (doc1)
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# ---------------------------------------------------------------------------
# Bucket Policy — enforce TLS and deny non-HTTPS access
# ---------------------------------------------------------------------------

resource "aws_s3_bucket_policy" "gdpr_exports" {
  bucket = aws_s3_bucket.gdpr_exports.id

  # Wait for public access block to be applied before attaching policy
  depends_on = [aws_s3_bucket_public_access_block.gdpr_exports]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.gdpr_exports.arn,
          "${aws_s3_bucket.gdpr_exports.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "DenyPublicAccess"
        Effect    = "Deny"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:PutObject"]
        Resource  = "${aws_s3_bucket.gdpr_exports.arn}/*"
        Condition = {
          StringNotEquals = {
            "aws:PrincipalAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Access Logging Bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "access_logs" {
  bucket        = "${var.project_name}-${var.environment}-s3-access-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.force_destroy

  tags = {
    Name = "${var.project_name}-${var.environment}-s3-access-logs"
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "log-retention"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_logging" "gdpr_exports" {
  bucket = aws_s3_bucket.gdpr_exports.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "gdpr-exports/"
}
