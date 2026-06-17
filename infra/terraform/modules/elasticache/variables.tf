variable "project_name" {
  description = "Project identifier used in resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment: dev, staging, or prod."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the ElastiCache cluster will be created."
  type        = string
}

variable "vpc_cidr_block" {
  description = "VPC CIDR block for security group ingress rules."
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the ElastiCache subnet group."
  type        = list(string)
}

variable "node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t3.micro"
}

variable "num_cache_clusters" {
  description = "Number of cache clusters in the replication group."
  type        = number
  default     = 1
}

variable "engine_version" {
  description = "Redis engine version."
  type        = string
  default     = "7.1"
}

variable "redis_port" {
  description = "Redis port number."
  type        = number
  default     = 6379
}
