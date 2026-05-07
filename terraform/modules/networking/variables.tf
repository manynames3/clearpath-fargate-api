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
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs for the ALB tier."
  type        = list(string)
}

variable "private_ecs_subnet_cidrs" {
  description = "Private subnet CIDRs for ECS Fargate tasks."
  type        = list(string)
}

variable "private_aurora_subnet_cidrs" {
  description = "Private subnet CIDRs for Aurora PostgreSQL."
  type        = list(string)
}

variable "interface_endpoint_services" {
  description = "AWS interface endpoint services ECS tasks need without public egress."
  type        = list(string)
  default = [
    "ecr.api",
    "ecr.dkr",
    "logs",
    "secretsmanager"
  ]
}
