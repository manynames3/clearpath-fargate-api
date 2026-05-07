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

variable "aurora_secret_arn" {
  description = "Aurora managed master user secret ARN."
  type        = string
}

variable "aurora_kms_key_arn" {
  description = "Aurora KMS key ARN used for the RDS-managed secret."
  type        = string
}

variable "rds_proxy_resource_id" {
  description = "RDS Proxy resource ID for rds-db:connect."
  type        = string
}

variable "database_username" {
  description = "Database username used by the application."
  type        = string
}

variable "ecr_repository_name" {
  description = "ECR repository name from which ECS execution role may pull."
  type        = string
}

variable "ecs_log_group_name" {
  description = "CloudWatch log group name for ECS container logs."
  type        = string
}
