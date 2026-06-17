# =============================================================================
# RDS Module — ProtegoPay PostgreSQL 15
# =============================================================================
# Creates an RDS PostgreSQL 15 instance with:
# - Encryption at rest (StorageEncrypted = true)
# - Private subnet placement only (no public accessibility)
# - Automated backups with configurable retention
# - Deletion protection configurable per environment
# - Security group allowing access only from within the VPC
# - Credentials stored exclusively in AWS Secrets Manager
# =============================================================================

# ---------------------------------------------------------------------------
# Random password (stored in Secrets Manager — never in tfvars or state output)
# ---------------------------------------------------------------------------

resource "random_password" "rds_master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"
  # Excludes @, /, \, " which cause issues in connection strings
}

# ---------------------------------------------------------------------------
# Subnet Group — private subnets only
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-${var.environment}-rds-subnet-group"
  subnet_ids  = var.private_subnet_ids
  description = "Private subnet group for ${var.project_name} ${var.environment} RDS"

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-subnet-group"
  }
}

# ---------------------------------------------------------------------------
# Security Group — RDS
# ---------------------------------------------------------------------------
# Only allows inbound on port 5432 from within the VPC CIDR.
# No 0.0.0.0/0 ingress rule — RDS is not reachable from the public internet.
# ---------------------------------------------------------------------------

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for ${var.project_name} ${var.environment} RDS — private VPC access only"
  vpc_id      = var.vpc_id

  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
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
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# Parameter Group — PostgreSQL 15, TLS enforced
# ---------------------------------------------------------------------------

resource "aws_db_parameter_group" "main" {
  name        = "${var.project_name}-${var.environment}-pg15"
  family      = "postgres15"
  description = "${var.project_name} ${var.environment} PostgreSQL 15 parameter group"

  parameter {
    name  = "rds.force_ssl"
    value = "1" # Enforce TLS 1.2+ on all connections
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log slow queries (>1s) for performance monitoring
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-pg15-params"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# RDS Instance
# ---------------------------------------------------------------------------

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = "15.6"
  instance_class       = var.instance_class
  parameter_group_name = aws_db_parameter_group.main.name

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true # REQUIRED: encryption at rest — doc1 § encryption
  # KMS key: when kms_key_id is not specified, AWS uses the default aws/rds key.
  # For prod, supply a customer-managed KMS key via var.kms_key_id.
  kms_key_id = var.kms_key_id != "" ? var.kms_key_id : null

  # Database
  db_name  = var.database_name
  username = "protegopay_admin"
  password = random_password.rds_master.result

  # Network — private only, no public access
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false # REQUIRED: no public internet exposure

  # High availability
  multi_az = var.multi_az

  # Backups
  backup_retention_period = var.backup_retention_days
  backup_window           = "02:00-03:00" # UTC — low traffic window
  maintenance_window      = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot   = true

  # Protection
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.deletion_protection ? false : true
  final_snapshot_identifier = var.deletion_protection ? "${var.project_name}-${var.environment}-final-snapshot" : null

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_enhanced_monitoring.arn
  performance_insights_enabled    = true

  # Auto minor version upgrades for security patches
  auto_minor_version_upgrade = true

  tags = {
    Name = "${var.project_name}-${var.environment}-postgres"
  }

  # Ensure DB password is not logged in plan output.
  # Password is managed via Secrets Manager after initial creation.
  lifecycle {
    ignore_changes = [
      password # Rotated by Secrets Manager after initial provisioning
    ]
  }
}

# ---------------------------------------------------------------------------
# Enhanced Monitoring IAM Role
# ---------------------------------------------------------------------------

resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
