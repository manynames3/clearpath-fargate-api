output "vpc_id" {
  description = "ID of the Clearpath VPC."
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the Clearpath VPC."
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs intended for the ALB."
  value       = [for subnet in aws_subnet.public : subnet.id]
}

output "private_ecs_subnet_ids" {
  description = "Private subnet IDs intended for ECS Fargate tasks."
  value       = [for subnet in aws_subnet.private_ecs : subnet.id]
}

output "private_aurora_subnet_ids" {
  description = "Private subnet IDs intended for Aurora PostgreSQL."
  value       = [for subnet in aws_subnet.private_aurora : subnet.id]
}

output "alb_sg_id" {
  description = "Security group ID for the ALB."
  value       = aws_security_group.alb.id
}

output "ecs_sg_id" {
  description = "Security group ID for ECS Fargate tasks."
  value       = aws_security_group.ecs.id
}

output "rds_proxy_sg_id" {
  description = "Security group ID for RDS Proxy."
  value       = aws_security_group.rds_proxy.id
}

output "aurora_sg_id" {
  description = "Security group ID for Aurora PostgreSQL."
  value       = aws_security_group.aurora.id
}

output "vpc_endpoint_sg_id" {
  description = "Security group ID for private interface endpoints."
  value       = aws_security_group.vpc_endpoint.id
}
