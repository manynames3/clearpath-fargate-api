data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  ecr_repository_arn = "arn:${data.aws_partition.current.partition}:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/${var.ecr_repository_name}"
  ecs_log_group_arn  = "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${var.ecs_log_group_name}"
}

data "aws_iam_policy_document" "app_secrets_kms" {
  #checkov:skip=CKV_AWS_111:KMS key policies use Resource "*" to refer to the current key; principals and service constraints limit use.
  #checkov:skip=CKV_AWS_356:KMS key policies use Resource "*" to refer to the current key; principals and service constraints limit use.
  #checkov:skip=CKV_AWS_109:Account-root administration is scoped to this key policy and required to avoid orphaned KMS keys.
  statement {
    sid = "EnableAccountKeyAdministration"
    actions = [
      "kms:CancelKeyDeletion",
      "kms:CreateAlias",
      "kms:CreateGrant",
      "kms:Decrypt",
      "kms:DeleteAlias",
      "kms:DescribeKey",
      "kms:DisableKey",
      "kms:EnableKey",
      "kms:EnableKeyRotation",
      "kms:Encrypt",
      "kms:GetKeyPolicy",
      "kms:GetKeyRotationStatus",
      "kms:ListAliases",
      "kms:ListGrants",
      "kms:ListKeyPolicies",
      "kms:PutKeyPolicy",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo",
      "kms:RetireGrant",
      "kms:RevokeGrant",
      "kms:ScheduleKeyDeletion",
      "kms:UpdateAlias",
      "kms:UpdateKeyDescription"
    ]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  statement {
    sid = "AllowSecretsManagerUseOfKey"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:GenerateDataKeyWithoutPlaintext",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo"
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["secretsmanager.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_kms_key" "app_secrets" {
  description             = "KMS key for ${var.project} ${var.env} application secrets"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.app_secrets_kms.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-app-secrets"
  })
}

resource "aws_kms_alias" "app_secrets" {
  name          = "alias/${var.project}-${var.env}-app-secrets"
  target_key_id = aws_kms_key.app_secrets.key_id
}

resource "aws_secretsmanager_secret" "ghl_webhook" {
  #checkov:skip=CKV2_AWS_57:Webhook secret value is loaded out-of-band to avoid plaintext in Terraform state; external rotation is documented in the runbook.
  name                    = "clearpath/${var.env}/ghl-webhook"
  description             = "GoHighLevel webhook HMAC secret for Clearpath API"
  kms_key_id              = aws_kms_key.app_secrets.arn
  recovery_window_in_days = 0

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ghl-webhook"
  })
}

data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.project}-${var.env}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-task"
  })
}

data "aws_iam_policy_document" "ecs_task" {
  statement {
    sid = "ReadRuntimeSecrets"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      var.database_secret_arn,
      aws_secretsmanager_secret.ghl_webhook.arn
    ]
  }

  statement {
    sid       = "DecryptRuntimeSecrets"
    actions   = ["kms:Decrypt"]
    resources = [var.database_kms_key_arn, aws_kms_key.app_secrets.arn]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }

  statement {
    sid       = "ConnectToRDSProxyAsAppUser"
    actions   = ["rds-db:connect"]
    resources = ["arn:${data.aws_partition.current.partition}:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:${var.rds_proxy_resource_id}/${var.database_username}"]
  }
}

resource "aws_iam_role_policy" "ecs_task" {
  name   = "${var.project}-${var.env}-ecs-task"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task.json
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${var.project}-${var.env}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-execution"
  })
}

data "aws_iam_policy_document" "ecs_execution" {
  statement {
    sid = "PullFromExactECRRepository"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = [local.ecr_repository_arn]
  }

  statement {
    sid = "AuthenticateToECR"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    # AWS requires GetAuthorizationToken to use Resource "*"; it cannot be scoped to a repository ARN.
    resources = ["*"]
  }

  statement {
    sid = "WriteContainerLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${local.ecs_log_group_arn}:*"]
  }
}

resource "aws_iam_role_policy" "ecs_execution" {
  name   = "${var.project}-${var.env}-ecs-execution"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution.json
}
