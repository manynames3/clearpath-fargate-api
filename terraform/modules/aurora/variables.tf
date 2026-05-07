variable "project" {
  description = "Project tag value applied to all resources."
  type        = string
}

variable "env" {
  description = "Deployment environment name."
  type        = string
}

variable "aws_region" {
  description = "AWS region for regional resources."
  type        = string
}

variable "aurora_subnet_ids" {
  description = "Private subnet IDs for the Aurora cluster subnet group."
  type        = list(string)
}

variable "rds_proxy_subnet_ids" {
  description = "Private subnet IDs where RDS Proxy endpoints are placed."
  type        = list(string)
}

variable "aurora_sg_id" {
  description = "Security group ID attached to Aurora."
  type        = string
}

variable "rds_proxy_sg_id" {
  description = "Security group ID attached to RDS Proxy."
  type        = string
}

variable "database_name" {
  description = "Initial database name."
  type        = string
  default     = "clearpath"
}

variable "master_username" {
  description = "Aurora master username."
  type        = string
  default     = "clearpath_admin"
}

variable "engine_version" {
  description = "Aurora PostgreSQL engine version. PostgreSQL 15.7+ is required for Serverless v2 auto-pause on the 15.x line."
  type        = string
  default     = "15.7"
}

variable "ca_cert_identifier" {
  description = "RDS CA certificate identifier for the Aurora instance."
  type        = string
  default     = "rds-ca-rsa2048-g1"
}

variable "aurora_min_capacity" {
  description = "Minimum Serverless v2 ACUs. Use 0 to enable auto-pause; use 0.5 if the target engine version does not support scale-to-zero."
  type        = number
  default     = 0
}

variable "aurora_max_capacity" {
  description = "Maximum Serverless v2 ACUs."
  type        = number
  default     = 4
}

variable "aurora_auto_pause_seconds" {
  description = "Idle seconds before Aurora Serverless v2 auto-pauses."
  type        = number
  default     = 300
}

variable "backup_retention_days" {
  description = "Aurora backup retention in days."
  type        = number
  default     = 7
}
