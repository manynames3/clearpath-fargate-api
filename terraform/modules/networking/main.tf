data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  public_subnets = {
    for idx, cidr in var.public_subnet_cidrs : idx => {
      cidr = cidr
      az   = var.availability_zones[idx]
    }
  }

  private_ecs_subnets = {
    for idx, cidr in var.private_ecs_subnet_cidrs : idx => {
      cidr = cidr
      az   = var.availability_zones[idx]
    }
  }

  private_aurora_subnets = {
    for idx, cidr in var.private_aurora_subnet_cidrs : idx => {
      cidr = cidr
      az   = var.availability_zones[idx]
    }
  }

  flow_log_group_name = "/aws/vpc/${var.project}/${var.env}/flow-logs"
  flow_log_group_arn  = "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.flow_log_group_name}"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}"
  })
}

resource "aws_default_security_group" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-default-deny"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-igw"
  })
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.az
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-public-${each.value.az}"
    Tier = "public"
  })
}

resource "aws_subnet" "private_ecs" {
  for_each = local.private_ecs_subnets

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.az
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-${each.value.az}"
    Tier = "private-ecs"
  })
}

resource "aws_subnet" "private_aurora" {
  for_each = local.private_aurora_subnets

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.az
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-aurora-${each.value.az}"
    Tier = "private-aurora"
  })
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-nat-eip"
  })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public["0"].id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-nat"
  })

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-public"
  })
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private_ecs" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-private-ecs"
  })
}

resource "aws_route_table_association" "private_ecs" {
  for_each = aws_subnet.private_ecs

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_ecs.id
}

resource "aws_route_table" "private_aurora" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-private-aurora"
  })
}

resource "aws_route_table_association" "private_aurora" {
  for_each = aws_subnet.private_aurora

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_aurora.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_ecs.id]

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-s3-endpoint"
  })
}

#checkov:skip=CKV2_AWS_5:Attached to VPC interface endpoints in this module.
resource "aws_security_group" "vpc_endpoint" {
  name_prefix            = "${var.project}-${var.env}-vpce-"
  description            = "Interface endpoint access from ECS tasks"
  vpc_id                 = aws_vpc.main.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-vpce"
  })
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(var.interface_endpoint_services)

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for subnet in aws_subnet.private_ecs : subnet.id]
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-${replace(each.value, ".", "-")}-endpoint"
  })
}

data "aws_iam_policy_document" "flow_logs_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "vpc_flow_logs" {
  name               = "${var.project}-${var.env}-vpc-flow-logs"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-vpc-flow-logs"
  })
}

data "aws_iam_policy_document" "vpc_flow_logs" {
  statement {
    sid = "WriteToExactFlowLogGroup"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]
    # CloudWatch log streams are created dynamically; the wildcard is scoped to this exact log group.
    resources = ["${local.flow_log_group_arn}:*"]
  }

  statement {
    sid       = "DescribeExactFlowLogGroup"
    actions   = ["logs:DescribeLogGroups"]
    resources = [local.flow_log_group_arn]
  }
}

resource "aws_iam_role_policy" "vpc_flow_logs" {
  name   = "${var.project}-${var.env}-vpc-flow-logs"
  role   = aws_iam_role.vpc_flow_logs.id
  policy = data.aws_iam_policy_document.vpc_flow_logs.json
}

data "aws_iam_policy_document" "flow_logs_kms" {
  #checkov:skip=CKV_AWS_111:KMS key policies use Resource "*" to refer to the current key; principals and encryption context constrain use.
  #checkov:skip=CKV_AWS_356:KMS key policies use Resource "*" to refer to the current key; principals and encryption context constrain use.
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
      values   = [local.flow_log_group_arn]
    }
  }
}

resource "aws_kms_key" "flow_logs" {
  description             = "KMS key for ${var.project} ${var.env} VPC flow logs"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.flow_logs_kms.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-flow-logs"
  })
}

resource "aws_kms_alias" "flow_logs" {
  name          = "alias/${var.project}-${var.env}-flow-logs"
  target_key_id = aws_kms_key.flow_logs.key_id
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = local.flow_log_group_name
  retention_in_days = 365
  kms_key_id        = aws_kms_key.flow_logs.arn

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-vpc-flow-logs"
  })
}

resource "aws_flow_log" "vpc" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-vpc-flow-logs"
  })
}

resource "aws_security_group" "alb" {
  #checkov:skip=CKV2_AWS_5:Attached to ALB in the ECS phase.
  name_prefix            = "${var.project}-${var.env}-alb-"
  description            = "ALB accepts HTTPS from CloudFront only"
  vpc_id                 = aws_vpc.main.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-alb"
  })
}

resource "aws_security_group" "ecs" {
  #checkov:skip=CKV2_AWS_5:Attached to ECS service in the ECS phase.
  name_prefix            = "${var.project}-${var.env}-ecs-"
  description            = "ECS tasks accept app traffic from ALB only"
  vpc_id                 = aws_vpc.main.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs"
  })
}

resource "aws_security_group" "rds_proxy" {
  #checkov:skip=CKV2_AWS_5:Attached to RDS Proxy in the Aurora phase.
  name_prefix            = "${var.project}-${var.env}-rds-proxy-"
  description            = "RDS Proxy accepts PostgreSQL from ECS only"
  vpc_id                 = aws_vpc.main.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-rds-proxy"
  })
}

resource "aws_security_group" "aurora" {
  #checkov:skip=CKV2_AWS_5:Attached to Aurora cluster in the Aurora phase.
  name_prefix            = "${var.project}-${var.env}-aurora-"
  description            = "Aurora accepts PostgreSQL from RDS Proxy only"
  vpc_id                 = aws_vpc.main.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-aurora"
  })
}

resource "aws_vpc_security_group_ingress_rule" "alb_from_cloudfront" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from CloudFront only"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-alb-from-cloudfront"
  })
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ecs" {
  security_group_id            = aws_security_group.alb.id
  description                  = "App port to ECS tasks only"
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-alb-to-ecs"
  })
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "App port from ALB only"
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-from-alb"
  })
}

resource "aws_vpc_security_group_egress_rule" "ecs_to_rds_proxy" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "PostgreSQL to RDS Proxy only"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.rds_proxy.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-to-rds-proxy"
  })
}

resource "aws_vpc_security_group_egress_rule" "ecs_to_interface_endpoints" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "HTTPS to AWS interface endpoints only"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.vpc_endpoint.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-to-vpce"
  })
}

resource "aws_vpc_security_group_egress_rule" "ecs_to_s3_endpoint" {
  security_group_id = aws_security_group.ecs.id
  description       = "HTTPS to S3 gateway endpoint for ECR image layers"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  prefix_list_id    = aws_vpc_endpoint.s3.prefix_list_id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs-to-s3"
  })
}

resource "aws_vpc_security_group_ingress_rule" "vpc_endpoint_from_ecs" {
  security_group_id            = aws_security_group.vpc_endpoint.id
  description                  = "HTTPS from ECS tasks only"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-vpce-from-ecs"
  })
}

resource "aws_vpc_security_group_ingress_rule" "rds_proxy_from_ecs" {
  security_group_id            = aws_security_group.rds_proxy.id
  description                  = "PostgreSQL from ECS only"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-rds-proxy-from-ecs"
  })
}

resource "aws_vpc_security_group_egress_rule" "rds_proxy_to_aurora" {
  security_group_id            = aws_security_group.rds_proxy.id
  description                  = "PostgreSQL to Aurora only"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.aurora.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-rds-proxy-to-aurora"
  })
}

resource "aws_vpc_security_group_ingress_rule" "aurora_from_rds_proxy" {
  security_group_id            = aws_security_group.aurora.id
  description                  = "PostgreSQL from RDS Proxy only"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.rds_proxy.id

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-aurora-from-rds-proxy"
  })
}
