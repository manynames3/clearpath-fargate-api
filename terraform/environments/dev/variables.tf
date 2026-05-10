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

variable "private_database_subnet_cidrs" {
  description = "Private subnet CIDRs for RDS PostgreSQL."
  type        = list(string)

  validation {
    condition     = length(var.private_database_subnet_cidrs) == 2
    error_message = "Phase 1 expects exactly two database subnet CIDRs."
  }
}

variable "database_name" {
  description = "Initial RDS database name."
  type        = string
}

variable "master_username" {
  description = "RDS master username."
  type        = string
}

variable "postgres_engine_version" {
  description = "RDS PostgreSQL engine version."
  type        = string
}

variable "rds_instance_class" {
  description = "RDS instance class for the current cost-controlled stage."
  type        = string
}

variable "rds_allocated_storage_gb" {
  description = "Initial RDS allocated storage in GiB."
  type        = number
}

variable "rds_max_allocated_storage_gb" {
  description = "Maximum RDS storage autoscaling limit in GiB."
  type        = number
}

variable "rds_multi_az" {
  description = "Whether to run RDS in Multi-AZ mode. Keep false for cost-controlled validation."
  type        = bool
}

variable "rds_deletion_protection" {
  description = "Whether deletion protection is enabled for RDS. Keep false for ephemeral teardown; enable for production."
  type        = bool
}

variable "rds_skip_final_snapshot" {
  description = "Whether to skip the final RDS snapshot on destroy. Keep true for ephemeral teardown; set false for production."
  type        = bool
}

variable "rds_final_snapshot_identifier" {
  description = "Final snapshot identifier to use when rds_skip_final_snapshot is false."
  type        = string
  default     = null
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

variable "alb_deletion_protection" {
  description = "Whether deletion protection is enabled for the ALB. Keep false for ephemeral teardown; enable for production."
  type        = bool
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

variable "origin_header_name" {
  description = "Custom header name CloudFront sends and ALB listener rules require when origin protection is enabled."
  type        = string
  default     = "X-Clearpath-Origin-Token"
}

variable "origin_header_value" {
  description = "Custom header value CloudFront sends and ALB listener rules require. Set through TF_VAR_origin_header_value for deployment; do not commit real values."
  type        = string
  default     = null
  sensitive   = true
  nullable    = true
}
