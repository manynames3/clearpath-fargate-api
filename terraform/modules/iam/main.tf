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
  ecs_service_arn    = "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${var.project}-${var.env}/clearpath-api"
  create_github_deploy_role = (
    var.github_deploy_repository != ""
  )
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
      "kms:ListResourceTags",
      "kms:PutKeyPolicy",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo",
      "kms:RetireGrant",
      "kms:RevokeGrant",
      "kms:ScheduleKeyDeletion",
      "kms:TagResource",
      "kms:UntagResource",
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
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [data.aws_caller_identity.current.account_id]
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

resource "aws_secretsmanager_secret" "api_key" {
  #checkov:skip=CKV2_AWS_57:API key value is loaded out-of-band to avoid plaintext in Terraform state; external rotation is documented in the runbook.
  name                    = "clearpath/${var.env}/api-key"
  description             = "API key for protected Clearpath lead query endpoints"
  kms_key_id              = aws_kms_key.app_secrets.arn
  recovery_window_in_days = 0

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-api-key"
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
      aws_secretsmanager_secret.ghl_webhook.arn,
      aws_secretsmanager_secret.api_key.arn
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

data "aws_iam_openid_connect_provider" "github" {
  count = local.create_github_deploy_role ? 1 : 0

  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_actions_deploy_assume" {
  count = local.create_github_deploy_role ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_deploy_repository}:ref:refs/heads/${var.github_deploy_branch}"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  count = local.create_github_deploy_role ? 1 : 0

  name               = "${var.project}-${var.env}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_actions_deploy_assume[0].json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-github-deploy"
  })
}

data "aws_iam_policy_document" "github_actions_deploy" {
  count = local.create_github_deploy_role ? 1 : 0

  statement {
    sid = "AuthenticateToECR"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    # AWS requires GetAuthorizationToken to use Resource "*"; it cannot be scoped to a repository ARN.
    resources = ["*"]
  }

  statement {
    sid = "PushToExactRepository"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeRepositories",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]
    resources = [local.ecr_repository_arn]
  }

  statement {
    sid = "RedeployExactService"
    actions = [
      "ecs:DescribeServices",
      "ecs:UpdateService"
    ]
    resources = [local.ecs_service_arn]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  count = local.create_github_deploy_role ? 1 : 0

  name   = "${var.project}-${var.env}-github-deploy"
  role   = aws_iam_role.github_actions_deploy[0].id
  policy = data.aws_iam_policy_document.github_actions_deploy[0].json
}
