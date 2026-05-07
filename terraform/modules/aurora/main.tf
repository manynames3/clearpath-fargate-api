data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  cluster_identifier            = "${var.project}-${var.env}"
  rds_os_metrics_log_group_name = "RDSOSMetrics"
  rds_os_metrics_log_group_arn  = "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.rds_os_metrics_log_group_name}"
  rds_proxy_resource_id         = element(split(":", aws_db_proxy.main.arn), 6)
}

data "aws_iam_policy_document" "aurora_kms" {
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
    sid = "AllowRDSUseOfKey"
    actions = [
      "kms:CreateGrant",
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
      identifiers = ["rds.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["rds.${var.aws_region}.amazonaws.com"]
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

  statement {
    sid = "AllowCloudWatchLogsEncryption"
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
      identifiers = ["logs.${var.aws_region}.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = [local.rds_os_metrics_log_group_arn]
    }
  }
}

resource "aws_kms_key" "aurora" {
  description             = "KMS key for ${var.project} ${var.env} Aurora storage and managed secret"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.aurora_kms.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-aurora"
  })
}

resource "aws_kms_alias" "aurora" {
  name          = "alias/${var.project}-${var.env}-aurora"
  target_key_id = aws_kms_key.aurora.key_id
}

resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project}-${var.env}-aurora"
  subnet_ids = var.aurora_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-aurora"
  })
}

resource "aws_rds_cluster_parameter_group" "main" {
  name        = "${var.project}-${var.env}-aurora-postgres15"
  family      = "aurora-postgresql15"
  description = "Aurora PostgreSQL query logging for ${var.project} ${var.env}"

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-aurora-postgres15"
  })
}

resource "aws_rds_cluster" "main" {
  #checkov:skip=CKV_AWS_139:Deletion protection is intentionally disabled for demo teardown.
  #checkov:skip=CKV_AWS_133:Managed master user password creates the secret; rotation is handled by RDS-managed credentials.
  #checkov:skip=CKV2_AWS_8:AWS Backup plan is intentionally omitted because this portfolio environment is disposable and teardown-first.
  cluster_identifier                  = local.cluster_identifier
  database_name                       = var.database_name
  db_cluster_parameter_group_name     = aws_rds_cluster_parameter_group.main.name
  db_subnet_group_name                = aws_db_subnet_group.aurora.name
  deletion_protection                 = false
  enabled_cloudwatch_logs_exports     = ["postgresql"]
  engine                              = "aurora-postgresql"
  engine_mode                         = "provisioned"
  engine_version                      = var.engine_version
  iam_database_authentication_enabled = true
  kms_key_id                          = aws_kms_key.aurora.arn
  manage_master_user_password         = true
  master_user_secret_kms_key_id       = aws_kms_key.aurora.arn
  master_username                     = var.master_username
  skip_final_snapshot                 = true
  storage_encrypted                   = true
  storage_type                        = "aurora"
  vpc_security_group_ids              = [var.aurora_sg_id]

  backup_retention_period = var.backup_retention_days
  copy_tags_to_snapshot   = true

  serverlessv2_scaling_configuration {
    max_capacity             = var.aurora_max_capacity
    min_capacity             = var.aurora_min_capacity
    seconds_until_auto_pause = var.aurora_auto_pause_seconds
  }

  tags = merge(local.common_tags, {
    Name = local.cluster_identifier
  })
}

resource "aws_cloudwatch_log_group" "rds_os_metrics" {
  name              = local.rds_os_metrics_log_group_name
  retention_in_days = 365
  kms_key_id        = aws_kms_key.aurora.arn

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-rds-os-metrics"
  })
}

data "aws_iam_policy_document" "rds_enhanced_monitoring_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  name               = "${var.project}-${var.env}-rds-enhanced-monitoring"
  assume_role_policy = data.aws_iam_policy_document.rds_enhanced_monitoring_assume.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-rds-enhanced-monitoring"
  })
}

data "aws_iam_policy_document" "rds_enhanced_monitoring" {
  statement {
    sid = "WriteRDSOSMetrics"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]
    resources = ["${local.rds_os_metrics_log_group_arn}:*"]
  }

  statement {
    sid       = "DescribeRDSOSMetrics"
    actions   = ["logs:DescribeLogGroups"]
    resources = [local.rds_os_metrics_log_group_arn]
  }
}

resource "aws_iam_role_policy" "rds_enhanced_monitoring" {
  name   = "${var.project}-${var.env}-rds-enhanced-monitoring"
  role   = aws_iam_role.rds_enhanced_monitoring.id
  policy = data.aws_iam_policy_document.rds_enhanced_monitoring.json
}

resource "aws_rds_cluster_instance" "main" {
  identifier                            = "${local.cluster_identifier}-1"
  auto_minor_version_upgrade            = true
  ca_cert_identifier                    = var.ca_cert_identifier
  cluster_identifier                    = aws_rds_cluster.main.id
  db_subnet_group_name                  = aws_db_subnet_group.aurora.name
  engine                                = aws_rds_cluster.main.engine
  engine_version                        = aws_rds_cluster.main.engine_version
  instance_class                        = "db.serverless"
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.rds_enhanced_monitoring.arn
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = aws_kms_key.aurora.arn
  performance_insights_retention_period = 7
  publicly_accessible                   = false

  tags = merge(local.common_tags, {
    Name = "${local.cluster_identifier}-1"
  })
}

data "aws_iam_policy_document" "rds_proxy_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "rds_proxy" {
  name               = "${var.project}-${var.env}-rds-proxy"
  assume_role_policy = data.aws_iam_policy_document.rds_proxy_assume.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-rds-proxy"
  })
}

data "aws_iam_policy_document" "rds_proxy" {
  statement {
    sid = "ReadAuroraManagedSecret"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [aws_rds_cluster.main.master_user_secret[0].secret_arn]
  }

  statement {
    sid       = "DecryptAuroraManagedSecret"
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.aurora.arn]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "rds_proxy" {
  name   = "${var.project}-${var.env}-rds-proxy"
  role   = aws_iam_role.rds_proxy.id
  policy = data.aws_iam_policy_document.rds_proxy.json
}

resource "aws_db_proxy" "main" {
  name                   = "${var.project}-proxy-${var.env}"
  debug_logging          = false
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_security_group_ids = [var.rds_proxy_sg_id]
  vpc_subnet_ids         = var.rds_proxy_subnet_ids

  auth {
    auth_scheme = "SECRETS"
    description = "Aurora managed master secret"
    iam_auth    = "REQUIRED"
    secret_arn  = aws_rds_cluster.main.master_user_secret[0].secret_arn
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-proxy-${var.env}"
  })

  depends_on = [aws_iam_role_policy.rds_proxy]
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    connection_borrow_timeout    = 120
    max_connections_percent      = 90
    max_idle_connections_percent = 50
  }
}

resource "aws_db_proxy_target" "main" {
  db_cluster_identifier = aws_rds_cluster.main.id
  db_proxy_name         = aws_db_proxy.main.name
  target_group_name     = aws_db_proxy_default_target_group.main.name
}
