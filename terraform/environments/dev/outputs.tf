output "vpc_id" {
  description = "ID of the Clearpath VPC."
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs intended for the ALB."
  value       = module.networking.public_subnet_ids
}

output "private_ecs_subnet_ids" {
  description = "Private subnet IDs intended for ECS Fargate tasks."
  value       = module.networking.private_ecs_subnet_ids
}

output "private_database_subnet_ids" {
  description = "Private subnet IDs intended for RDS PostgreSQL."
  value       = module.networking.private_database_subnet_ids
}

output "alb_sg_id" {
  description = "Security group ID for the public ALB."
  value       = module.networking.alb_sg_id
}

output "ecs_sg_id" {
  description = "Security group ID for ECS Fargate tasks."
  value       = module.networking.ecs_sg_id
}

output "rds_proxy_sg_id" {
  description = "Security group ID for RDS Proxy."
  value       = module.networking.rds_proxy_sg_id
}

output "database_sg_id" {
  description = "Security group ID for RDS PostgreSQL."
  value       = module.networking.database_sg_id
}

output "db_instance_identifier" {
  description = "RDS DB instance identifier."
  value       = module.rds.db_instance_identifier
}

output "database_secret_arn" {
  description = "RDS-managed Secrets Manager ARN for database credentials."
  value       = module.rds.master_user_secret_arn
}

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint hostname."
  value       = module.rds.rds_proxy_endpoint
}

output "rds_proxy_name" {
  description = "RDS Proxy name."
  value       = module.rds.rds_proxy_name
}

output "rds_proxy_resource_id" {
  description = "RDS Proxy resource ID used in rds-db:connect ARNs."
  value       = module.rds.rds_proxy_resource_id
}

output "ghl_webhook_secret_arn" {
  description = "GHL webhook secret ARN."
  value       = module.iam.ghl_webhook_secret_arn
}

output "api_key_secret_arn" {
  description = "Protected lead query API key secret ARN."
  value       = module.iam.api_key_secret_arn
}

output "ecr_repository_url" {
  description = "ECR repository URL."
  value       = module.ecs.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = module.ecs.service_name
}

output "alb_dns_name" {
  description = "ALB DNS name."
  value       = module.ecs.alb_dns_name
}

output "api_certificate_arn" {
  description = "ACM certificate ARN used by ALB and CloudFront when custom-domain mode is enabled."
  value       = module.dns_certificate.certificate_arn
}

output "custom_domain_enabled" {
  description = "Whether this environment is using ACM/Route53 custom-domain mode."
  value       = local.custom_domain_enabled
}

output "api_base_url" {
  description = "Base URL for API smoke tests. Defaults to the generated CloudFront domain when no custom domain is configured."
  value       = local.custom_domain_enabled ? "https://${var.api_domain_name}" : "https://${module.cloudfront.distribution_domain_name}"
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID."
  value       = module.cloudfront.distribution_id
}

output "waf_web_acl_arn" {
  description = "CloudFront WAF WebACL ARN."
  value       = module.cloudfront.waf_web_acl_arn
}

output "cloudwatch_dashboard_name" {
  description = "CloudWatch dashboard name."
  value       = module.observability.dashboard_name
}
