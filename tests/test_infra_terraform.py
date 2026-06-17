"""
Structural validation tests for ProtegoPay Terraform infrastructure.

These tests verify the Terraform configuration files are present,
correctly structured, and enforce all security contract requirements
(doc1_security_contract.md) WITHOUT requiring live AWS credentials.

They test the code, not the deployed infrastructure.
"""

import os
import re
import pytest

# Root of the infra/terraform directory
TERRAFORM_DIR = os.path.join(os.path.dirname(__file__), "..", "infra", "terraform")
MODULES_DIR = os.path.join(TERRAFORM_DIR, "modules")
ENV_DIR = os.path.join(TERRAFORM_DIR, "env")


def read_tf(path):
    """Read a Terraform file. Returns empty string if not found."""
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def tf_attr(content, key, value):
    """
    Check that a Terraform attribute assignment exists.
    Handles variable whitespace between key, =, and value.
    e.g. tf_attr(content, "storage_encrypted", "true")
    """
    pattern = rf"^\s*{re.escape(key)}\s*=\s*{re.escape(value)}"
    return bool(re.search(pattern, content, re.MULTILINE))


# ─────────────────────────────────────────────────────────────────────────────
# Module presence tests
# ─────────────────────────────────────────────────────────────────────────────


class TestModuleStructure:
    """All required modules must exist."""

    def test_vpc_module_exists(self):
        assert os.path.isfile(os.path.join(MODULES_DIR, "vpc", "main.tf")), (
            "vpc/main.tf must exist"
        )

    def test_rds_module_exists(self):
        assert os.path.isfile(os.path.join(MODULES_DIR, "rds", "main.tf")), (
            "rds/main.tf must exist"
        )

    def test_elasticache_module_exists(self):
        assert os.path.isfile(os.path.join(MODULES_DIR, "elasticache", "main.tf")), (
            "elasticache/main.tf must exist"
        )

    def test_s3_module_exists(self):
        assert os.path.isfile(os.path.join(MODULES_DIR, "s3", "main.tf")), (
            "s3/main.tf must exist"
        )

    def test_secrets_manager_module_exists(self):
        assert os.path.isfile(
            os.path.join(MODULES_DIR, "secrets_manager", "main.tf")
        ), "secrets_manager/main.tf must exist"

    def test_all_modules_have_outputs(self):
        for mod in ["vpc", "rds", "elasticache", "s3", "secrets_manager"]:
            path = os.path.join(MODULES_DIR, mod, "outputs.tf")
            assert os.path.isfile(path), f"{mod}/outputs.tf must exist"

    def test_all_modules_have_variables(self):
        for mod in ["vpc", "rds", "elasticache", "s3", "secrets_manager"]:
            path = os.path.join(MODULES_DIR, mod, "variables.tf")
            assert os.path.isfile(path), f"{mod}/variables.tf must exist"


# ─────────────────────────────────────────────────────────────────────────────
# Environment configuration tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEnvironmentConfigs:
    """Three isolated environments must be defined."""

    def test_dev_tfvars_exists(self):
        assert os.path.isfile(os.path.join(ENV_DIR, "dev.tfvars")), (
            "dev.tfvars must exist"
        )

    def test_staging_tfvars_exists(self):
        assert os.path.isfile(os.path.join(ENV_DIR, "staging.tfvars")), (
            "staging.tfvars must exist"
        )

    def test_prod_tfvars_exists(self):
        assert os.path.isfile(os.path.join(ENV_DIR, "prod.tfvars")), (
            "prod.tfvars must exist"
        )

    def test_dev_backend_hcl_exists(self):
        assert os.path.isfile(os.path.join(ENV_DIR, "dev.backend.hcl")), (
            "dev.backend.hcl must exist"
        )

    def test_staging_backend_hcl_exists(self):
        assert os.path.isfile(os.path.join(ENV_DIR, "staging.backend.hcl")), (
            "staging.backend.hcl must exist"
        )

    def test_prod_backend_hcl_exists(self):
        assert os.path.isfile(os.path.join(ENV_DIR, "prod.backend.hcl")), (
            "prod.backend.hcl must exist"
        )

    def test_environments_have_different_vpc_cidrs(self):
        """Each environment must have a different VPC CIDR (no routing overlap)."""
        dev = read_tf(os.path.join(ENV_DIR, "dev.tfvars"))
        staging = read_tf(os.path.join(ENV_DIR, "staging.tfvars"))
        prod = read_tf(os.path.join(ENV_DIR, "prod.tfvars"))

        def extract_vpc_cidr(content):
            m = re.search(r'vpc_cidr\s*=\s*"([^"]+)"', content)
            return m.group(1) if m else None

        dev_cidr = extract_vpc_cidr(dev)
        staging_cidr = extract_vpc_cidr(staging)
        prod_cidr = extract_vpc_cidr(prod)

        assert dev_cidr is not None, "dev.tfvars must define vpc_cidr"
        assert staging_cidr is not None, "staging.tfvars must define vpc_cidr"
        assert prod_cidr is not None, "prod.tfvars must define vpc_cidr"

        assert dev_cidr != staging_cidr, "dev and staging VPC CIDRs must differ"
        assert dev_cidr != prod_cidr, "dev and prod VPC CIDRs must differ"
        assert staging_cidr != prod_cidr, "staging and prod VPC CIDRs must differ"

    def test_prod_deletion_protection_enabled(self):
        """Production must have RDS deletion protection enabled."""
        prod = read_tf(os.path.join(ENV_DIR, "prod.tfvars"))
        assert tf_attr(prod, "rds_deletion_protection", "true"), (
            "prod.tfvars must set rds_deletion_protection = true"
        )

    def test_prod_multi_az_enabled(self):
        """Production must have RDS Multi-AZ enabled."""
        prod = read_tf(os.path.join(ENV_DIR, "prod.tfvars"))
        assert tf_attr(prod, "rds_multi_az", "true"), (
            "prod.tfvars must set rds_multi_az = true"
        )

    def test_environments_have_separate_state_keys(self):
        """Each environment must use a separate Terraform state key."""
        dev = read_tf(os.path.join(ENV_DIR, "dev.backend.hcl"))
        staging = read_tf(os.path.join(ENV_DIR, "staging.backend.hcl"))
        prod = read_tf(os.path.join(ENV_DIR, "prod.backend.hcl"))

        def extract_key(content):
            m = re.search(r'key\s*=\s*"([^"]+)"', content)
            return m.group(1) if m else None

        dev_key = extract_key(dev)
        staging_key = extract_key(staging)
        prod_key = extract_key(prod)

        assert dev_key != staging_key, "dev and staging must use different state keys"
        assert dev_key != prod_key, "dev and prod must use different state keys"
        assert staging_key != prod_key, "staging and prod must use different state keys"

    def test_backend_encrypt_enabled(self):
        """All backend configs must have encrypt = true."""
        for env in ["dev", "staging", "prod"]:
            content = read_tf(os.path.join(ENV_DIR, f"{env}.backend.hcl"))
            assert tf_attr(content, "encrypt", "true"), (
                f"{env}.backend.hcl must set encrypt = true"
            )

    def test_backend_uses_dynamodb_for_locking(self):
        """All backend configs must specify a DynamoDB table for state locking."""
        for env in ["dev", "staging", "prod"]:
            content = read_tf(os.path.join(ENV_DIR, f"{env}.backend.hcl"))
            assert "dynamodb_table" in content, (
                f"{env}.backend.hcl must define dynamodb_table for state locking"
            )

    def test_backend_in_eu_central_1(self):
        """All backend configs must use eu-central-1 (EU/EEA requirement)."""
        for env in ["dev", "staging", "prod"]:
            content = read_tf(os.path.join(ENV_DIR, f"{env}.backend.hcl"))
            assert "eu-central-1" in content, (
                f"{env}.backend.hcl must use eu-central-1 region"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Security contract compliance tests — RDS
# ─────────────────────────────────────────────────────────────────────────────


class TestRDSSecurity:
    """RDS must be encrypted, private, and not publicly accessible."""

    def setup_method(self, method):
        self.main = read_tf(os.path.join(MODULES_DIR, "rds", "main.tf"))

    def test_storage_encrypted_true(self):
        """RDS StorageEncrypted must be true."""
        assert tf_attr(self.main, "storage_encrypted", "true"), (
            "RDS main.tf must set storage_encrypted = true"
        )

    def test_publicly_accessible_false(self):
        """RDS must not be publicly accessible."""
        assert tf_attr(self.main, "publicly_accessible", "false"), (
            "RDS main.tf must set publicly_accessible = false"
        )

    def test_no_public_cidr_in_rds_ingress(self):
        """RDS security group must not allow 0.0.0.0/0 ingress on port 5432."""
        # Extract ingress block for RDS (port 5432)
        ingress_section = re.search(
            r"ingress\s*\{[^}]*from_port\s*=\s*5432[^}]*\}",
            self.main,
            re.DOTALL,
        )
        if ingress_section:
            ingress_text = ingress_section.group(0)
            assert "0.0.0.0/0" not in ingress_text, (
                "RDS security group ingress on port 5432 must not allow 0.0.0.0/0"
            )

    def test_uses_private_subnet_group(self):
        """RDS must use a subnet group composed of private subnets."""
        assert "aws_db_subnet_group" in self.main, (
            "RDS main.tf must define a subnet group"
        )
        assert "private_subnet_ids" in self.main, (
            "RDS subnet group must use private_subnet_ids"
        )

    def test_backup_retention_configured(self):
        """RDS must have automated backup retention configured."""
        assert "backup_retention_period" in self.main, (
            "RDS main.tf must set backup_retention_period"
        )

    def test_tls_enforced_via_parameter_group(self):
        """RDS must enforce TLS via rds.force_ssl parameter."""
        assert "rds.force_ssl" in self.main, (
            "RDS must enforce TLS via rds.force_ssl parameter group"
        )

    def test_password_marked_sensitive(self):
        """RDS password output must be marked sensitive."""
        outputs = read_tf(os.path.join(MODULES_DIR, "rds", "outputs.tf"))
        assert tf_attr(outputs, "sensitive", "true"), (
            "RDS password output must be marked sensitive = true"
        )

    def test_kms_encryption_output_exists(self):
        """RDS must export KMS key ID for documentation."""
        outputs = read_tf(os.path.join(MODULES_DIR, "rds", "outputs.tf"))
        assert "kms_key_id" in outputs, (
            "RDS outputs must expose kms_key_id for documentation"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Security contract compliance tests — ElastiCache Redis
# ─────────────────────────────────────────────────────────────────────────────


class TestElastiCacheSecurity:
    """Redis must be encrypted, private, and require auth."""

    def setup_method(self, method):
        self.main = read_tf(os.path.join(MODULES_DIR, "elasticache", "main.tf"))

    def test_at_rest_encryption_enabled(self):
        """Redis at-rest encryption must be enabled."""
        assert tf_attr(self.main, "at_rest_encryption_enabled", "true"), (
            "ElastiCache main.tf must set at_rest_encryption_enabled = true"
        )

    def test_transit_encryption_enabled(self):
        """Redis TLS (transit encryption) must be enabled."""
        assert tf_attr(self.main, "transit_encryption_enabled", "true"), (
            "ElastiCache main.tf must set transit_encryption_enabled = true"
        )

    def test_transit_encryption_mode_required(self):
        """Redis TLS mode must be 'required', not 'preferred'."""
        assert tf_attr(self.main, "transit_encryption_mode", '"required"'), (
            "ElastiCache must set transit_encryption_mode = required"
        )

    def test_auth_token_configured(self):
        """Redis must require an auth token."""
        assert "auth_token" in self.main, (
            "ElastiCache main.tf must configure auth_token"
        )

    def test_uses_private_subnet_group(self):
        """Redis must use a private subnet group."""
        assert "aws_elasticache_subnet_group" in self.main, (
            "ElastiCache must define a subnet group"
        )
        assert "private_subnet_ids" in self.main, (
            "ElastiCache subnet group must use private_subnet_ids"
        )

    def test_no_public_cidr_in_redis_ingress(self):
        """Redis security group must not allow 0.0.0.0/0 ingress on redis port."""
        ingress_section = re.search(
            r"ingress\s*\{[^}]*from_port\s*=\s*var\.redis_port[^}]*\}",
            self.main,
            re.DOTALL,
        )
        if ingress_section:
            ingress_text = ingress_section.group(0)
            assert "0.0.0.0/0" not in ingress_text, (
                "Redis security group ingress must not allow 0.0.0.0/0"
            )

    def test_auth_token_marked_sensitive(self):
        """Redis auth token output must be marked sensitive."""
        outputs = read_tf(os.path.join(MODULES_DIR, "elasticache", "outputs.tf"))
        assert tf_attr(outputs, "sensitive", "true"), (
            "ElastiCache auth_token output must be marked sensitive = true"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Security contract compliance tests — S3 GDPR Bucket
# ─────────────────────────────────────────────────────────────────────────────


class TestS3Security:
    """S3 GDPR bucket must block all public access and use encryption."""

    def setup_method(self, method):
        self.main = read_tf(os.path.join(MODULES_DIR, "s3", "main.tf"))

    def test_block_public_acls_true(self):
        assert tf_attr(self.main, "block_public_acls", "true"), (
            "S3 must set block_public_acls = true"
        )

    def test_block_public_policy_true(self):
        assert tf_attr(self.main, "block_public_policy", "true"), (
            "S3 must set block_public_policy = true"
        )

    def test_ignore_public_acls_true(self):
        assert tf_attr(self.main, "ignore_public_acls", "true"), (
            "S3 must set ignore_public_acls = true"
        )

    def test_restrict_public_buckets_true(self):
        assert tf_attr(self.main, "restrict_public_buckets", "true"), (
            "S3 must set restrict_public_buckets = true"
        )

    def test_versioning_enabled(self):
        assert "aws_s3_bucket_versioning" in self.main, (
            "S3 must configure bucket versioning"
        )
        assert '"Enabled"' in self.main, "S3 versioning must be Enabled"

    def test_server_side_encryption_configured(self):
        assert "aws_s3_bucket_server_side_encryption_configuration" in self.main, (
            "S3 must configure server-side encryption"
        )

    def test_lifecycle_policy_configured(self):
        assert "aws_s3_bucket_lifecycle_configuration" in self.main, (
            "S3 must configure lifecycle rules for GDPR data retention"
        )

    def test_no_public_bucket_policy(self):
        """The bucket policy must not grant public read or write."""
        # Look for any Principal with "*" in a bucket policy Allow statement
        policy_pattern = re.search(
            r'"Effect"\s*:\s*"Allow".*?"Principal"\s*:\s*"\*"',
            self.main,
            re.DOTALL,
        )
        assert policy_pattern is None, (
            "S3 bucket policy must not grant public access (Principal: *)"
        )

    def test_ssl_only_bucket_policy(self):
        """S3 bucket policy must deny non-TLS requests."""
        assert "aws:SecureTransport" in self.main, (
            "S3 bucket policy must enforce TLS (aws:SecureTransport condition)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Security contract compliance tests — Secrets Manager
# ─────────────────────────────────────────────────────────────────────────────


class TestSecretsManagerSecurity:
    """All required secrets must exist; no plaintext values in Terraform code."""

    def setup_method(self, method):
        self.main = read_tf(os.path.join(MODULES_DIR, "secrets_manager", "main.tf"))

    def test_db_url_secret_created(self):
        assert "DB_URL" in self.main, "Secrets Manager must create DB_URL secret"

    def test_redis_url_secret_created(self):
        assert "REDIS_URL" in self.main, "Secrets Manager must create REDIS_URL secret"

    def test_jwt_secret_created(self):
        assert "JWT_SECRET" in self.main, "Secrets Manager must create JWT_SECRET"

    def test_webhook_hmac_secret_created(self):
        assert "WEBHOOK_HMAC_SECRET" in self.main, (
            "Secrets Manager must create WEBHOOK_HMAC_SECRET"
        )

    def test_kms_encryption_for_secrets(self):
        """All secrets must be encrypted with a KMS key."""
        assert "aws_kms_key" in self.main, (
            "Secrets Manager must use a KMS key for encryption"
        )
        assert "kms_key_id" in self.main, (
            "Secrets Manager secrets must reference the KMS key"
        )

    def test_kms_key_rotation_enabled(self):
        """KMS key must have automatic rotation enabled."""
        assert tf_attr(self.main, "enable_key_rotation", "true"), (
            "KMS key must have enable_key_rotation = true"
        )

    def test_no_plaintext_secret_values_in_tfvars(self):
        """
        No tfvars file should contain actual secret values.
        Real passwords would contain long random strings or obvious credential patterns.
        Placeholders like REPLACE_AFTER_PROVISIONING are acceptable.
        """
        for env in ["dev", "staging", "prod"]:
            content = read_tf(os.path.join(ENV_DIR, f"{env}.tfvars"))
            # Verify no real-looking secret key values appear
            assert "jwt_secret" not in content.lower(), (
                f"{env}.tfvars must not contain jwt_secret value"
            )

    def test_initial_secret_values_are_placeholders(self):
        """Initial secret values set by Terraform must be placeholders."""
        assert (
            "REPLACE_AFTER_PROVISIONING" in self.main
            or "placeholder" in self.main.lower()
        ), "Secrets Manager initial values must be placeholders, not real secrets"

    def test_ignore_changes_on_secret_values(self):
        """Terraform must ignore_changes on secret values to prevent overwriting rotated secrets."""
        assert "ignore_changes" in self.main and "secret_string" in self.main, (
            "Secrets must have lifecycle ignore_changes = [secret_string]"
        )

    def test_iam_policy_for_application_access(self):
        """An IAM policy for the application to read secrets must exist."""
        assert "aws_iam_policy" in self.main, (
            "Secrets Manager must create an IAM policy for application secret access"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Backend and state management tests
# ─────────────────────────────────────────────────────────────────────────────


class TestTerraformBackend:
    """State must be stored in S3+DynamoDB, not the repository."""

    def setup_method(self, method):
        self.backend = read_tf(os.path.join(TERRAFORM_DIR, "backend.tf"))

    def test_s3_backend_configured(self):
        assert 'backend "s3"' in self.backend, "backend.tf must configure S3 backend"

    def test_encrypt_enabled_in_backend(self):
        assert "encrypt" in self.backend, "backend.tf must reference encrypt option"

    def test_dynamodb_table_referenced(self):
        assert "dynamodb_table" in self.backend, (
            "backend.tf must reference DynamoDB table for state locking"
        )

    def test_terraform_version_requirement(self):
        assert "required_version" in self.backend, (
            "backend.tf must specify required Terraform version"
        )

    def test_aws_provider_region_enforced(self):
        """AWS provider must use eu-central-1."""
        assert "eu-central-1" in self.backend, (
            "backend.tf must specify eu-central-1 region"
        )

    def test_tfstate_files_gitignored(self):
        """*.tfstate files must be gitignored."""
        gitignore_path = os.path.join(os.path.dirname(__file__), "..", ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                content = f.read()
            assert "*.tfstate" in content, ".gitignore must exclude *.tfstate files"
        else:
            pytest.skip(".gitignore not found — skipping gitignore check")

    def test_dot_terraform_gitignored(self):
        """The .terraform/ directory must be gitignored."""
        gitignore_path = os.path.join(os.path.dirname(__file__), "..", ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                content = f.read()
            assert ".terraform/" in content, (
                ".gitignore must exclude .terraform/ directory"
            )
        else:
            pytest.skip(".gitignore not found — skipping gitignore check")


# ─────────────────────────────────────────────────────────────────────────────
# Root module composition tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRootModule:
    """Root module must compose all required sub-modules."""

    def setup_method(self, method):
        self.main = read_tf(os.path.join(TERRAFORM_DIR, "main.tf"))
        self.outputs = read_tf(os.path.join(TERRAFORM_DIR, "outputs.tf"))
        self.variables = read_tf(os.path.join(TERRAFORM_DIR, "variables.tf"))

    def test_vpc_module_called(self):
        assert 'module "vpc"' in self.main, "Root main.tf must call the vpc module"

    def test_rds_module_called(self):
        assert 'module "rds"' in self.main, "Root main.tf must call the rds module"

    def test_elasticache_module_called(self):
        assert 'module "elasticache"' in self.main, (
            "Root main.tf must call the elasticache module"
        )

    def test_s3_module_called(self):
        assert 'module "s3"' in self.main, "Root main.tf must call the s3 module"

    def test_secrets_manager_module_called(self):
        assert 'module "secrets_manager"' in self.main, (
            "Root main.tf must call the secrets_manager module"
        )

    def test_environment_variable_defined(self):
        assert 'variable "environment"' in self.variables, (
            "variables.tf must define the environment variable"
        )

    def test_environment_validation(self):
        """Environment variable must be validated to only allow dev/staging/prod."""
        assert (
            '"dev"' in self.variables
            and '"staging"' in self.variables
            and '"prod"' in self.variables
        ), "variables.tf must validate environment is one of: dev, staging, prod"

    def test_region_validation(self):
        """AWS region must be validated to eu-central-1."""
        assert "eu-central-1" in self.variables and "validation" in self.variables, (
            "variables.tf must validate aws_region = eu-central-1"
        )

    def test_rds_encryption_output(self):
        """Root outputs must expose RDS storage_encrypted for documentation."""
        assert "rds_storage_encrypted" in self.outputs, (
            "outputs.tf must expose rds_storage_encrypted"
        )

    def test_rds_kms_key_output(self):
        """Root outputs must expose RDS KMS key ARN."""
        assert "rds_kms_key_id" in self.outputs, "outputs.tf must expose rds_kms_key_id"

    def test_s3_public_access_block_output(self):
        """Root outputs must expose S3 public access block confirmation."""
        assert "s3_public_access_block" in self.outputs, (
            "outputs.tf must expose s3_public_access_block"
        )

    def test_secret_arns_in_outputs_not_values(self):
        """Root outputs must expose secret ARNs, not secret values."""
        # Confirm secret ARNs are output (for documentation)
        assert "db_url_secret_arn" in self.outputs, (
            "outputs.tf must expose db_url_secret_arn"
        )
        assert "jwt_secret_arn" in self.outputs, "outputs.tf must expose jwt_secret_arn"
        assert "webhook_hmac_secret_arn" in self.outputs, (
            "outputs.tf must expose webhook_hmac_secret_arn"
        )


# ─────────────────────────────────────────────────────────────────────────────
# .env security tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEnvFileSecurity:
    """The .env file must be gitignored; .env.example must contain only placeholders."""

    BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

    def test_env_file_gitignored(self):
        """The .env file must be listed in .gitignore."""
        gitignore_path = os.path.join(self.BASE_DIR, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                content = f.read()
            assert ".env" in content, (
                ".gitignore must list .env to prevent secret leakage"
            )

    def test_infra_env_example_exists(self):
        """infra/.env.example must exist to document local dev setup."""
        assert os.path.isfile(os.path.join(self.BASE_DIR, "infra", ".env.example")), (
            "infra/.env.example must exist"
        )

    def test_infra_env_example_has_no_real_secrets(self):
        """infra/.env.example must not contain real secret values."""
        path = os.path.join(self.BASE_DIR, "infra", ".env.example")
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            lines = content.splitlines()
            for line in lines:
                if "=" in line and not line.strip().startswith("#"):
                    _, _, value = line.partition("=")
                    value = value.strip()
                    # infra/.env.example only has comments and empty values
                    # Values > 40 chars that don't start with < are suspicious
                    if value and len(value) > 40 and not value.startswith("<"):
                        pytest.fail(
                            "infra/.env.example appears to contain a real secret value"
                        )

    def test_readme_exists(self):
        """infra/README.md must exist to document the infrastructure."""
        assert os.path.isfile(os.path.join(self.BASE_DIR, "infra", "README.md")), (
            "infra/README.md must exist"
        )


# ─────────────────────────────────────────────────────────────────────────────
# VPC network isolation tests
# ─────────────────────────────────────────────────────────────────────────────


class TestVPCNetworkIsolation:
    """VPC must have proper private/public subnet separation."""

    def setup_method(self, method):
        self.main = read_tf(os.path.join(MODULES_DIR, "vpc", "main.tf"))

    def test_private_subnets_have_no_public_ip(self):
        """Private subnets must not auto-assign public IPs."""
        # Find private subnet resource block
        private_subnet_block = re.search(
            r'resource "aws_subnet" "private".*?(?=resource|\Z)',
            self.main,
            re.DOTALL,
        )
        if private_subnet_block:
            block_text = private_subnet_block.group(0)
            assert tf_attr(block_text, "map_public_ip_on_launch", "false"), (
                "Private subnets must set map_public_ip_on_launch = false"
            )

    def test_internet_gateway_exists(self):
        """VPC must have an Internet Gateway for public subnets."""
        assert "aws_internet_gateway" in self.main, (
            "VPC must define an Internet Gateway"
        )

    def test_nat_gateway_exists(self):
        """Private subnet egress must use NAT Gateway."""
        assert "aws_nat_gateway" in self.main, (
            "VPC must define NAT Gateway for private subnet egress"
        )

    def test_vpc_flow_logs_enabled(self):
        """VPC Flow Logs must be enabled for security monitoring."""
        assert "aws_flow_log" in self.main, (
            "VPC must enable flow logs for security monitoring"
        )

    def test_private_route_table_uses_nat(self):
        """Private route tables must route through NAT Gateway, not IGW."""
        # Private route table should reference nat_gateway, not internet_gateway
        # for the default route
        private_rt_block = re.search(
            r'resource "aws_route_table" "private".*?(?=resource|\Z)',
            self.main,
            re.DOTALL,
        )
        if private_rt_block:
            rt_text = private_rt_block.group(0)
            assert "nat_gateway" in rt_text, (
                "Private route table must route through NAT Gateway"
            )
            # Ensure internet gateway is not the target for private route table default route
            assert (
                "internet_gateway" not in rt_text
                or "aws_internet_gateway" not in rt_text
            ), "Private route table must not route directly to Internet Gateway"
