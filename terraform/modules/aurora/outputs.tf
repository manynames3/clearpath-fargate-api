output "cluster_arn" {
  description = "Aurora cluster ARN."
  value       = aws_rds_cluster.main.arn
}

output "cluster_identifier" {
  description = "Aurora cluster identifier."
  value       = aws_rds_cluster.main.cluster_identifier
}

output "database_name" {
  description = "Aurora database name."
  value       = aws_rds_cluster.main.database_name
}

output "master_username" {
  description = "Aurora master username."
  value       = aws_rds_cluster.main.master_username
}

output "master_user_secret_arn" {
  description = "Secrets Manager ARN for the RDS-managed Aurora master user secret."
  value       = aws_rds_cluster.main.master_user_secret[0].secret_arn
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

output "aurora_kms_key_arn" {
  description = "KMS key ARN used by Aurora storage and the RDS-managed secret."
  value       = aws_kms_key.aurora.arn
}
