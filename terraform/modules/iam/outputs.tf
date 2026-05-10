output "ecs_task_role_arn" {
  description = "ECS task role ARN."
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_execution_role_arn" {
  description = "ECS execution role ARN."
  value       = aws_iam_role.ecs_execution.arn
}

output "ghl_webhook_secret_arn" {
  description = "Secrets Manager ARN for the GHL webhook HMAC secret."
  value       = aws_secretsmanager_secret.ghl_webhook.arn
}

output "api_key_secret_arn" {
  description = "Secrets Manager ARN for the protected lead query API key."
  value       = aws_secretsmanager_secret.api_key.arn
}

output "app_secrets_kms_key_arn" {
  description = "KMS key ARN for app-owned Secrets Manager secrets."
  value       = aws_kms_key.app_secrets.arn
}

output "github_deploy_role_arn" {
  description = "GitHub Actions OIDC deploy role ARN, when enabled."
  value       = try(aws_iam_role.github_actions_deploy[0].arn, "")
}
