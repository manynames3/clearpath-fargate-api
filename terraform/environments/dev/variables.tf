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

variable "vpc_cidr" {
  description = "CIDR block for the Clearpath VPC."
  type        = string
}

variable "availability_zones" {
  description = "Availability zones used by the subnet layout."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Phase 1 expects exactly two availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs for the ALB tier."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Phase 1 expects exactly two public subnet CIDRs."
  }
}

variable "private_ecs_subnet_cidrs" {
  description = "Private subnet CIDRs for ECS Fargate tasks."
  type        = list(string)

  validation {
    condition     = length(var.private_ecs_subnet_cidrs) == 2
    error_message = "Phase 1 expects exactly two ECS subnet CIDRs."
  }
}

variable "private_aurora_subnet_cidrs" {
  description = "Private subnet CIDRs for Aurora PostgreSQL."
  type        = list(string)

  validation {
    condition     = length(var.private_aurora_subnet_cidrs) == 2
    error_message = "Phase 1 expects exactly two Aurora subnet CIDRs."
  }
}

variable "database_name" {
  description = "Initial Aurora database name."
  type        = string
}

variable "master_username" {
  description = "Aurora master username."
  type        = string
}

variable "aurora_engine_version" {
  description = "Aurora PostgreSQL engine version."
  type        = string
}

variable "aurora_min_capacity" {
  description = "Minimum Aurora Serverless v2 ACUs."
  type        = number
}

variable "aurora_max_capacity" {
  description = "Maximum Aurora Serverless v2 ACUs."
  type        = number
}

variable "aurora_auto_pause_seconds" {
  description = "Idle seconds before Aurora Serverless v2 auto-pauses."
  type        = number
}

variable "app_database_username" {
  description = "Database username used by the application through RDS Proxy IAM auth."
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

variable "ecs_desired_count" {
  description = "Desired ECS task count."
  type        = number
}

variable "api_domain_name" {
  description = "Public API domain name served by CloudFront."
  type        = string
}

variable "origin_domain_name" {
  description = "Origin domain name that aliases to the ALB."
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID. Empty skips DNS records for local-only validation."
  type        = string
  default     = ""
}
