variable "project_name" {
  description = "Project identifier used in resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
}

variable "recovery_window_days" {
  description = "Days before a deleted secret is permanently purged (0 = immediate, 7-30 for scheduled)."
  type        = number
  default     = 7
}

variable "db_host" {
  description = "RDS endpoint hostname (no credentials). Used to populate the DB_URL placeholder."
  type        = string
  default     = ""
}

variable "db_name" {
  description = "Database name. Used to populate the DB_URL placeholder."
  type        = string
  default     = "protegopay"
}

variable "db_username" {
  description = "Database master username. Used to populate the DB_URL placeholder."
  type        = string
  default     = "protegopay_admin"
  sensitive   = true
}

variable "redis_host" {
  description = "Redis primary endpoint hostname (no credentials). Used to populate REDIS_URL placeholder."
  type        = string
  default     = ""
}

variable "redis_port" {
  description = "Redis port number."
  type        = number
  default     = 6379
}
