output "db_instance_arn" {
  description = "RDS DB instance ARN."
  value       = aws_db_instance.main.arn
}

output "db_instance_identifier" {
  description = "RDS DB instance identifier."
  value       = aws_db_instance.main.identifier
}

output "database_name" {
  description = "RDS database name."
  value       = aws_db_instance.main.db_name
}

output "master_username" {
  description = "RDS master username."
  value       = aws_db_instance.main.username
}

output "master_user_secret_arn" {
  description = "Secrets Manager ARN for the RDS-managed master user secret."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "rds_proxy_arn" {
  description = "RDS Proxy ARN."
  value       = aws_db_proxy.main.arn
}

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint hostname."
  value       = aws_db_proxy.main.endpoint
}

output "rds_proxy_name" {
  description = "RDS Proxy name."
  value       = aws_db_proxy.main.name
}

output "rds_proxy_resource_id" {
  description = "RDS Proxy resource ID used in rds-db:connect ARNs."
  value       = local.rds_proxy_resource_id
}

output "database_kms_key_arn" {
  description = "KMS key ARN used by RDS storage and the RDS-managed secret."
  value       = aws_kms_key.database.arn
}
