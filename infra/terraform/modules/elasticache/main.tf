# =============================================================================
# ElastiCache Redis Module — ProtegoPay
# =============================================================================
# Creates an ElastiCache Redis replication group with:
# - Private subnet placement only (no public internet exposure)
# - Encryption in transit (TLS) and at rest
# - Security group allowing access only from within the VPC
# - Auth token stored in AWS Secrets Manager
# - Used for: rate limiting, session blacklisting, refresh token rotation
# =============================================================================

# ---------------------------------------------------------------------------
# Random auth token (stored in Secrets Manager)
# ---------------------------------------------------------------------------

resource "random_password" "redis_auth_token" {
  length           = 32
  special          = false # Redis auth token does not support all special chars
}

# ---------------------------------------------------------------------------
# Subnet Group — private subnets only
# ---------------------------------------------------------------------------

resource "aws_elasticache_subnet_group" "main" {
  name        = "${var.project_name}-${var.environment}-redis-subnet-group"
  subnet_ids  = var.private_subnet_ids
  description = "Private subnet group for ${var.project_name} ${var.environment} Redis"

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-subnet-group"
  }
}

# ---------------------------------------------------------------------------
# Security Group — Redis
# ---------------------------------------------------------------------------
# Only allows inbound on port 6379 from within the VPC CIDR.
# No 0.0.0.0/0 ingress rule — Redis is not reachable from the public internet.
# ---------------------------------------------------------------------------

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-${var.environment}-redis-sg"
  description = "Security group for ${var.project_name} ${var.environment} Redis — private VPC access only"
  vpc_id      = var.vpc_id

  ingress {
    description = "Redis from VPC"
    from_port   = var.redis_port
    to_port     = var.redis_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# Parameter Group
# ---------------------------------------------------------------------------

resource "aws_elasticache_parameter_group" "main" {
  name        = "${var.project_name}-${var.environment}-redis-params"
  family      = "redis7"
  description = "${var.project_name} ${var.environment} Redis parameter group"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru" # Evict only keys with TTL set (safe for blacklist keys)
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-params"
  }
}

# ---------------------------------------------------------------------------
# ElastiCache Replication Group (Redis cluster)
# ---------------------------------------------------------------------------

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.project_name}-${var.environment}-redis"
  description          = "${var.project_name} ${var.environment} Redis cluster for rate limiting and session blacklisting"

  # Engine
  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_clusters
  parameter_group_name = aws_elasticache_parameter_group.main.name
  port                 = var.redis_port

  # Network — private subnets only
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  # Security — encryption enforced
  at_rest_encryption_enabled  = true # Encryption at rest
  transit_encryption_enabled  = true # TLS 1.2+ in transit
  transit_encryption_mode     = "required"
  auth_token                  = random_password.redis_auth_token.result # Auth required

  # Maintenance and snapshots
  maintenance_window         = "sun:05:00-sun:06:00"
  snapshot_window            = "03:00-04:00"
  snapshot_retention_limit   = 7
  auto_minor_version_upgrade = true

  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "engine-log"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }

  lifecycle {
    ignore_changes = [
      auth_token # Rotated via Secrets Manager after initial provisioning
    ]
  }
}

# ---------------------------------------------------------------------------
# CloudWatch Log Groups for Redis
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${var.project_name}-${var.environment}/slow-log"
  retention_in_days = 90

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-slow-log"
  }
}

resource "aws_cloudwatch_log_group" "redis_engine" {
  name              = "/aws/elasticache/${var.project_name}-${var.environment}/engine-log"
  retention_in_days = 90

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-engine-log"
  }
}
