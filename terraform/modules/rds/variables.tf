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

variable "database_subnet_ids" {
  description = "Private subnet IDs for the RDS database subnet group."
  type        = list(string)
}

variable "rds_proxy_subnet_ids" {
  description = "Private subnet IDs where RDS Proxy endpoints are placed."
  type        = list(string)
}

variable "database_sg_id" {
  description = "Security group ID attached to RDS PostgreSQL."
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
  description = "RDS master username."
  type        = string
  default     = "clearpath_admin"
}

variable "engine_version" {
  description = "RDS PostgreSQL engine version."
  type        = string
  default     = "15.7"
}

variable "instance_class" {
  description = "RDS instance class for the current cost-controlled stage."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage_gb" {
  description = "Initial RDS allocated storage in GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage_gb" {
  description = "Maximum RDS storage autoscaling limit in GiB."
  type        = number
  default     = 100
}

variable "ca_cert_identifier" {
  description = "RDS CA certificate identifier for the PostgreSQL instance."
  type        = string
  default     = "rds-ca-rsa2048-g1"
}

variable "backup_retention_days" {
  description = "RDS backup retention in days."
  type        = number
  default     = 7
}

variable "multi_az" {
  description = "Whether to run RDS in Multi-AZ mode. Keep false for cost-controlled demos; enable for production availability."
  type        = bool
  default     = false
}
