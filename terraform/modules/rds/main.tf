data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  db_identifier                 = "${var.project}-${var.env}"
  rds_os_metrics_log_group_name = "RDSOSMetrics"
  rds_os_metrics_log_group_arn  = "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.rds_os_metrics_log_group_name}"
  rds_proxy_resource_id         = element(split(":", aws_db_proxy.main.arn), 6)
}

data "aws_iam_policy_document" "database_kms" {
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

resource "aws_kms_key" "database" {
  description             = "KMS key for ${var.project} ${var.env} RDS PostgreSQL storage and managed secret"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.database_kms.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-database"
  })
}

resource "aws_kms_alias" "database" {
  name          = "alias/${var.project}-${var.env}-database"
  target_key_id = aws_kms_key.database.key_id
}

resource "aws_db_subnet_group" "database" {
  name       = "${var.project}-${var.env}-database"
  subnet_ids = var.database_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-database"
  })
}

resource "aws_db_parameter_group" "main" {
  name        = "${var.project}-${var.env}-postgres15"
  family      = "postgres15"
  description = "RDS PostgreSQL query logging for ${var.project} ${var.env}"

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-postgres15"
  })
}

resource "aws_cloudwatch_log_group" "rds_os_metrics" {
  name              = local.rds_os_metrics_log_group_name
  retention_in_days = 365
  kms_key_id        = aws_kms_key.database.arn

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

resource "aws_db_instance" "main" {
  #checkov:skip=CKV_AWS_157:Single-AZ is intentional for the current cost-controlled demo stage; enable var.multi_az for production.
  #checkov:skip=CKV_AWS_133:RDS-managed master user password creates the secret without plaintext in Terraform state.
  #checkov:skip=CKV_AWS_16:Final snapshots are controlled by var.skip_final_snapshot; demo defaults skip them for teardown, production should set false.
  #checkov:skip=CKV_AWS_293:Deletion protection is controlled by var.deletion_protection; demo defaults disable it for teardown, production should enable it.
  #checkov:skip=CKV2_AWS_8:AWS Backup plan is intentionally omitted because this portfolio environment is disposable and teardown-first.
  identifier                          = local.db_identifier
  allocated_storage                   = var.allocated_storage_gb
  max_allocated_storage               = var.max_allocated_storage_gb
  auto_minor_version_upgrade          = true
  backup_retention_period             = var.backup_retention_days
  ca_cert_identifier                  = var.ca_cert_identifier
  copy_tags_to_snapshot               = true
  db_name                             = var.database_name
  db_subnet_group_name                = aws_db_subnet_group.database.name
  deletion_protection                 = var.deletion_protection
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]
  engine                              = "postgres"
  engine_version                      = var.engine_version
  iam_database_authentication_enabled = true
  instance_class                      = var.instance_class
  kms_key_id                          = aws_kms_key.database.arn
  manage_master_user_password         = true
  master_user_secret_kms_key_id       = aws_kms_key.database.arn
  monitoring_interval                 = 60
  monitoring_role_arn                 = aws_iam_role.rds_enhanced_monitoring.arn
  multi_az                            = var.multi_az
  parameter_group_name                = aws_db_parameter_group.main.name
  performance_insights_enabled        = true
  performance_insights_kms_key_id     = aws_kms_key.database.arn
  publicly_accessible                 = false
  final_snapshot_identifier           = var.final_snapshot_identifier
  skip_final_snapshot                 = var.skip_final_snapshot
  storage_encrypted                   = true
  storage_type                        = "gp3"
  username                            = var.master_username
  vpc_security_group_ids              = [var.database_sg_id]

  tags = merge(local.common_tags, {
    Name = local.db_identifier
  })

  lifecycle {
    precondition {
      condition     = var.skip_final_snapshot || var.final_snapshot_identifier != null
      error_message = "final_snapshot_identifier must be set when skip_final_snapshot is false."
    }
  }
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
    sid = "ReadRDSManagedSecret"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [aws_db_instance.main.master_user_secret[0].secret_arn]
  }

  statement {
    sid       = "DecryptRDSManagedSecret"
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.database.arn]

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
    description = "RDS managed master secret"
    iam_auth    = "REQUIRED"
    secret_arn  = aws_db_instance.main.master_user_secret[0].secret_arn
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
  db_instance_identifier = aws_db_instance.main.identifier
  db_proxy_name          = aws_db_proxy.main.name
  target_group_name      = aws_db_proxy_default_target_group.main.name
}
