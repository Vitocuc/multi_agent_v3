# =============================================================================
# Root Module — ProtegoPay Infrastructure
# =============================================================================
# Composes VPC, RDS, ElastiCache, S3, and Secrets Manager modules for a
# given environment (dev / staging / prod).
#
# Usage:
#   terraform init \
#     -backend-config="env/<workspace>.backend.hcl"
#   terraform workspace select <env>   # or: new <env>
#   terraform apply -var-file="env/<env>.tfvars"
#
# See infra/README.md for full bootstrap and post-provisioning instructions.
# =============================================================================

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------

module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL 15
# ---------------------------------------------------------------------------

module "rds" {
  source = "./modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  vpc_cidr_block        = module.vpc.vpc_cidr_block
  private_subnet_ids    = module.vpc.private_subnet_ids
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  database_name         = var.rds_database_name
  backup_retention_days = var.rds_backup_retention_days
  deletion_protection   = var.rds_deletion_protection
  multi_az              = var.rds_multi_az
}

# ---------------------------------------------------------------------------
# ElastiCache Redis
# ---------------------------------------------------------------------------

module "elasticache" {
  source = "./modules/elasticache"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  vpc_cidr_block     = module.vpc.vpc_cidr_block
  private_subnet_ids = module.vpc.private_subnet_ids
  node_type          = var.redis_node_type
  num_cache_clusters = var.redis_num_cache_clusters
  engine_version     = var.redis_engine_version
  redis_port         = var.redis_port
}

# ---------------------------------------------------------------------------
# S3 — GDPR Export Storage
# ---------------------------------------------------------------------------

module "s3" {
  source = "./modules/s3"

  project_name  = var.project_name
  environment   = var.environment
  force_destroy = var.s3_gdpr_force_destroy
}

# ---------------------------------------------------------------------------
# Secrets Manager
# ---------------------------------------------------------------------------

module "secrets_manager" {
  source = "./modules/secrets_manager"

  project_name         = var.project_name
  environment          = var.environment
  recovery_window_days = var.secrets_recovery_window_days

  # Pass non-secret infrastructure metadata to populate secret placeholders
  db_host    = module.rds.db_endpoint
  db_name    = module.rds.db_name
  db_username = module.rds.db_username
  redis_host  = module.elasticache.primary_endpoint_address
  redis_port  = module.elasticache.port
}
