# ProtegoPay Infrastructure

AWS eu-central-1 infrastructure provisioned via Terraform for the ProtegoPay platform.
Three isolated environments: **dev**, **staging**, **prod**.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  AWS eu-central-1  (VPC per environment)                    │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │ Public Subnets│   │Private Subnets│  │ AWS Services   │  │
│  │              │   │              │   │                │  │
│  │ NAT Gateway  │──▶│ RDS PG 15    │   │ Secrets Manager│  │
│  │ ALB (future) │   │ (encrypted)  │   │ S3 (GDPR)      │  │
│  │              │   │              │   │ CloudWatch     │  │
│  │              │   │ ElastiCache  │   │                │  │
│  │              │   │ Redis 7.1    │   │                │  │
│  └──────────────┘   └──────────────┘   └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Security properties:**
- RDS and Redis are in private subnets — unreachable from the public internet
- All storage encrypted at rest (RDS: KMS, Redis: KMS, S3: SSE-S3/KMS)
- TLS enforced on all endpoints (`rds.force_ssl=1`, Redis `transit_encryption_mode=required`)
- All public access blocked on S3 bucket
- VPC Flow Logs enabled

---

## Module Structure

```
infra/
├── terraform/
│   ├── backend.tf              # S3+DynamoDB remote state config
│   ├── main.tf                 # Root module — composes all modules
│   ├── variables.tf            # Global input variables
│   ├── outputs.tf              # Non-secret resource outputs
│   ├── env/
│   │   ├── dev.tfvars          # Dev environment sizing
│   │   ├── staging.tfvars      # Staging environment sizing
│   │   ├── prod.tfvars         # Prod environment sizing
│   │   ├── dev.backend.hcl     # Dev state backend coordinates
│   │   ├── staging.backend.hcl # Staging state backend coordinates
│   │   └── prod.backend.hcl    # Prod state backend coordinates
│   └── modules/
│       ├── vpc/                # VPC, subnets, IGW, NAT Gateways, Flow Logs
│       ├── rds/                # PostgreSQL 15, parameter group, monitoring
│       ├── elasticache/        # Redis 7.1 replication group
│       ├── s3/                 # GDPR exports bucket with lifecycle
│       └── secrets_manager/    # Secrets Manager secrets + KMS key
└── README.md                   # This file
```

---

## Prerequisites

### One-time S3 + DynamoDB bootstrap (per AWS account)

Before running `terraform init`, create the remote state bucket and lock table.
Run these AWS CLI commands once per account:

```bash
# Replace <ACCOUNT_ID> with your 12-digit AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Create versioned, encrypted state bucket
aws s3api create-bucket \
  --bucket "protegopay-terraform-state-${ACCOUNT_ID}" \
  --region eu-central-1 \
  --create-bucket-configuration LocationConstraint=eu-central-1

aws s3api put-bucket-versioning \
  --bucket "protegopay-terraform-state-${ACCOUNT_ID}" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "protegopay-terraform-state-${ACCOUNT_ID}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block \
  --bucket "protegopay-terraform-state-${ACCOUNT_ID}" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# 2. Create DynamoDB lock table
aws dynamodb create-table \
  --table-name protegopay-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-central-1
```

### IAM permissions required for Terraform

The IAM role/user running Terraform requires:
- `AmazonVPCFullAccess`
- `AmazonRDSFullAccess`
- `AmazonElastiCacheFullAccess`
- `AmazonS3FullAccess`
- `SecretsManagerReadWrite`
- `IAMFullAccess` (for IAM roles/policies created by modules)
- `CloudWatchLogsFullAccess`
- `KMSPowerUser` (for CMK creation)
- `DynamoDB:PutItem`, `GetItem`, `DeleteItem` on the lock table
- `S3:GetObject`, `PutObject`, `DeleteObject` on the state bucket

---

## Deployment

### Dev environment

```bash
cd infra/terraform

# Initialise with dev backend
terraform init -backend-config="env/dev.backend.hcl"

# Preview changes (review output — check for no secret leakage)
terraform plan -var-file="env/dev.tfvars"

# Apply
terraform apply -var-file="env/dev.tfvars"
```

### Staging environment

```bash
cd infra/terraform

terraform init -reconfigure -backend-config="env/staging.backend.hcl"
terraform plan -var-file="env/staging.tfvars"
terraform apply -var-file="env/staging.tfvars"
```

### Production environment

```bash
# Production requires human approval before apply.
cd infra/terraform

terraform init -reconfigure -backend-config="env/prod.backend.hcl"

# Review plan carefully — check for no secrets in output
terraform plan -var-file="env/prod.tfvars" -out=prod.tfplan

# Human review required here
terraform apply prod.tfplan
```

---

## Post-Provisioning: Populate Secrets

After `terraform apply`, populate the actual secret values in Secrets Manager.
**Never put secret values in tfvars or environment variables.**

```bash
# Example: set DB_URL after provisioning
aws secretsmanager put-secret-value \
  --region eu-central-1 \
  --secret-id "protegopay/<ENV>/DB_URL" \
  --secret-string '{"url":"postgresql://protegopay_admin:<PASSWORD>@<RDS_ENDPOINT>:5432/<DB_NAME>"}'

# Example: set JWT_SECRET
aws secretsmanager put-secret-value \
  --region eu-central-1 \
  --secret-id "protegopay/<ENV>/JWT_SECRET" \
  --secret-string '{"value":"<STRONG_RANDOM_32+_CHAR_SECRET>"}'
```

---

## Security Verification

### Verify RDS encryption at rest

```bash
aws rds describe-db-instances \
  --region eu-central-1 \
  --db-instance-identifier "protegopay-<ENV>-postgres" \
  --query 'DBInstances[0].{StorageEncrypted:StorageEncrypted,KmsKeyId:KmsKeyId}'
```

Expected output: `StorageEncrypted: true` and a non-null `KmsKeyId`.

### Verify RDS is not publicly accessible

```bash
aws rds describe-db-instances \
  --region eu-central-1 \
  --db-instance-identifier "protegopay-<ENV>-postgres" \
  --query 'DBInstances[0].PubliclyAccessible'
```

Expected output: `false`.

### Verify S3 public access block

```bash
aws s3api get-public-access-block \
  --bucket "protegopay-<ENV>-gdpr-exports-<ACCOUNT_ID>"
```

Expected: all four fields `true`.

### Verify Redis encryption

```bash
aws elasticache describe-replication-groups \
  --region eu-central-1 \
  --replication-group-id "protegopay-<ENV>-redis" \
  --query 'ReplicationGroups[0].{AtRestEncryptionEnabled:AtRestEncryptionEnabled,TransitEncryptionEnabled:TransitEncryptionEnabled}'
```

Expected: both `true`.

---

## Resource ARN Inventory

> Fill this section after `terraform apply` using `terraform output`.
> Never include secret values or connection strings with passwords here.

### Dev environment

| Resource | ARN / ID | Notes |
|---|---|---|
| VPC | _(fill after apply)_ | eu-central-1 |
| RDS Instance | _(fill after apply)_ | PostgreSQL 15, encrypted |
| ElastiCache | _(fill after apply)_ | Redis 7.1, TLS enabled |
| S3 GDPR Bucket | _(fill after apply)_ | All public access blocked |
| Secrets KMS Key | _(fill after apply)_ | Customer-managed key |
| DB_URL Secret ARN | _(fill after apply)_ | No secret value here |
| REDIS_URL Secret ARN | _(fill after apply)_ | No secret value here |
| JWT_SECRET ARN | _(fill after apply)_ | No secret value here |
| WEBHOOK_HMAC_SECRET ARN | _(fill after apply)_ | No secret value here |

### Staging environment

| Resource | ARN / ID | Notes |
|---|---|---|
| VPC | _(fill after apply)_ | eu-central-1 |
| RDS Instance | _(fill after apply)_ | PostgreSQL 15, Multi-AZ, encrypted |
| ElastiCache | _(fill after apply)_ | Redis 7.1, 2-node, TLS enabled |
| S3 GDPR Bucket | _(fill after apply)_ | All public access blocked |

### Production environment

| Resource | ARN / ID | Notes |
|---|---|---|
| VPC | _(fill after apply)_ | eu-central-1, isolated |
| RDS Instance | _(fill after apply)_ | PostgreSQL 15, Multi-AZ, deletion protection, encrypted |
| ElastiCache | _(fill after apply)_ | Redis 7.1, 3-node, TLS enabled |
| S3 GDPR Bucket | _(fill after apply)_ | All public access blocked |
| RDS KMS Key ARN | _(fill after apply)_ | Required by doc1 security contract |

---

## Environment Separation

Each environment uses:
- **Isolated VPC** with non-overlapping CIDR ranges (dev: 10.10/16, staging: 10.20/16, prod: 10.30/16)
- **Separate RDS instance** with a distinct database name and independent credentials
- **Separate ElastiCache cluster**
- **Separate S3 bucket** (bucket name includes environment)
- **Separate Secrets Manager path** (`protegopay/<env>/...`)
- **Separate Terraform state key** (`protegopay/<env>/terraform.tfstate`)

Cross-environment connections are impossible by network design — no VPC peering exists
between dev, staging, and prod. A staging database connection string cannot reach the
production RDS instance.

---

## Security Notes

1. **Terraform plan output**: Always review `terraform plan` output before applying.
   The `sensitive = true` marker on passwords and auth tokens ensures they do not
   appear in plan output. If any value you did not mark as sensitive appears in plan
   output looking like a secret, stop and investigate.

2. **State file**: The Terraform state file may contain resource IDs and non-sensitive
   metadata. It does NOT contain plaintext passwords (all passwords are generated with
   `random_password` and marked `sensitive`). However, treat the state bucket as
   sensitive and restrict access via IAM.

3. **Rotation**: DB and Redis passwords should be rotated after initial provisioning
   via AWS Secrets Manager rotation lambdas. The `lifecycle { ignore_changes = [password] }`
   and `lifecycle { ignore_changes = [auth_token] }` blocks prevent Terraform from
   resetting rotated credentials.

4. **.env files**: Never commit `.env` files. The `.gitignore` at the project root
   and `infra/.env.example` document the expected local development setup.
