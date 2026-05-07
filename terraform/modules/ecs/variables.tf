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

variable "vpc_id" {
  description = "VPC ID for ALB target groups."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks."
  type        = list(string)
}

variable "alb_sg_id" {
  description = "ALB security group ID."
  type        = string
}

variable "ecs_sg_id" {
  description = "ECS task security group ID."
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS task role ARN."
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ECS execution role ARN."
  type        = string
}

variable "ecr_repository_name" {
  description = "ECR repository name."
  type        = string
}

variable "ecs_log_group_name" {
  description = "ECS container log group name."
  type        = string
}

variable "database_name" {
  description = "Aurora database name."
  type        = string
}

variable "database_username" {
  description = "Database username used by the app."
  type        = string
}

variable "aurora_secret_arn" {
  description = "Aurora managed credential secret ARN."
  type        = string
}

variable "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint hostname."
  type        = string
}

variable "ghl_webhook_secret_arn" {
  description = "GHL webhook secret ARN."
  type        = string
}

variable "acm_cert_arn" {
  description = "ACM certificate ARN for the ALB HTTPS listener. Empty string defers listener creation until DNS/ACM is wired."
  type        = string
  default     = ""
}

variable "create_https_listener" {
  description = "Whether to create the ALB HTTPS listener and listener rules."
  type        = bool
  default     = true
}

variable "desired_count" {
  description = "Desired ECS task count."
  type        = number
  default     = 2
}
