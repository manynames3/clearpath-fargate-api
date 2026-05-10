data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  log_group_arn            = "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${var.ecs_log_group_name}"
  origin_header_conditions = var.origin_header_value == null ? [] : [var.origin_header_value]
}

data "aws_iam_policy_document" "ecs_kms" {
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
      values   = [local.log_group_arn]
    }
  }

  statement {
    sid = "AllowECRUseOfKey"
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
      identifiers = ["ecr.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ecr.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_kms_key" "ecs" {
  description             = "KMS key for ${var.project} ${var.env} ECS logs and ECR"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.ecs_kms.json

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs"
  })
}

resource "aws_kms_alias" "ecs" {
  name          = "alias/${var.project}-${var.env}-ecs"
  target_key_id = aws_kms_key.ecs.key_id
}

resource "aws_ecr_repository" "api" {
  #checkov:skip=CKV_AWS_51:The deployment workflow publishes a moving latest tag; immutable SHA tags are also pushed by CI.
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.ecs.arn
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = var.ecr_repository_name
  })
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = var.ecs_log_group_name
  retention_in_days = 365
  kms_key_id        = aws_kms_key.ecs.arn

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-ecs"
  })
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.env}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}"
  })
}

resource "aws_lb" "main" {
  #checkov:skip=CKV_AWS_91:ALB access logs are omitted for low-cost ephemeral teardown; CloudFront and ECS logs cover the request path.
  #checkov:skip=CKV_AWS_150:Deletion protection is controlled by var.alb_deletion_protection; dev defaults disable it for teardown, production should enable it.
  #checkov:skip=CKV2_AWS_28:WAF is attached to CloudFront, and the ALB security group only accepts CloudFront origin-facing traffic.
  #checkov:skip=CKV2_AWS_20:No-domain validation terminates HTTPS at CloudFront and allows HTTP only from CloudFront to the ALB generated DNS name.
  name                       = "${var.project}-alb-${var.env}"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [var.alb_sg_id]
  subnets                    = var.public_subnet_ids
  drop_invalid_header_fields = true
  enable_deletion_protection = var.alb_deletion_protection

  tags = merge(local.common_tags, {
    Name = "${var.project}-alb-${var.env}"
  })
}

resource "aws_lb_target_group" "api" {
  #checkov:skip=CKV_AWS_378:TLS terminates at the ALB; ALB-to-ECS traffic stays private and is restricted by security groups.
  name        = "${var.project}-api-${var.env}"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-api-${var.env}"
  })
}

resource "aws_lb_target_group" "webhooks" {
  #checkov:skip=CKV_AWS_378:TLS terminates at the ALB; ALB-to-ECS traffic stays private and is restricted by security groups.
  name        = "${var.project}-webhooks-${var.env}"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-webhooks-${var.env}"
  })
}

resource "aws_lb_listener" "https" {
  count = var.create_https_listener ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_cert_arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "application/json"
      message_body = "{\"detail\":\"not found\"}"
      status_code  = "404"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-https"
  })
}

resource "aws_lb_listener" "http" {
  #checkov:skip=CKV_AWS_2:No-domain validation terminates viewer TLS at CloudFront and uses HTTP only from the CloudFront origin-facing prefix list to the ALB generated DNS name.
  #checkov:skip=CKV_AWS_103:No-domain validation cannot attach an ACM certificate to the ALB generated DNS name; custom-domain mode creates the TLS 1.2 HTTPS listener.
  count = var.create_http_listener ? 1 : 0

  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "application/json"
      message_body = "{\"detail\":\"not found\"}"
      status_code  = "404"
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-http"
  })
}

resource "aws_lb_listener_rule" "health" {
  count = var.create_https_listener ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/health", "/ready"]
    }
  }

  dynamic "condition" {
    for_each = local.origin_header_conditions
    content {
      http_header {
        http_header_name = var.origin_header_name
        values           = [condition.value]
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-health"
  })
}

resource "aws_lb_listener_rule" "webhooks" {
  count = var.create_https_listener ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.webhooks.arn
  }

  condition {
    path_pattern {
      values = ["/webhooks/*"]
    }
  }

  dynamic "condition" {
    for_each = local.origin_header_conditions
    content {
      http_header {
        http_header_name = var.origin_header_name
        values           = [condition.value]
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-webhooks"
  })
}

resource "aws_lb_listener_rule" "api" {
  count = var.create_https_listener ? 1 : 0

  listener_arn = aws_lb_listener.https[0].arn
  priority     = 30

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  dynamic "condition" {
    for_each = local.origin_header_conditions
    content {
      http_header {
        http_header_name = var.origin_header_name
        values           = [condition.value]
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-api"
  })
}

resource "aws_lb_listener_rule" "http_health" {
  count = var.create_http_listener ? 1 : 0

  listener_arn = aws_lb_listener.http[0].arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/health", "/ready"]
    }
  }

  dynamic "condition" {
    for_each = local.origin_header_conditions
    content {
      http_header {
        http_header_name = var.origin_header_name
        values           = [condition.value]
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-http-health"
  })
}

resource "aws_lb_listener_rule" "http_webhooks" {
  count = var.create_http_listener ? 1 : 0

  listener_arn = aws_lb_listener.http[0].arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.webhooks.arn
  }

  condition {
    path_pattern {
      values = ["/webhooks/*"]
    }
  }

  dynamic "condition" {
    for_each = local.origin_header_conditions
    content {
      http_header {
        http_header_name = var.origin_header_name
        values           = [condition.value]
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-http-webhooks"
  })
}

resource "aws_lb_listener_rule" "http_api" {
  count = var.create_http_listener ? 1 : 0

  listener_arn = aws_lb_listener.http[0].arn
  priority     = 30

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  dynamic "condition" {
    for_each = local.origin_header_conditions
    content {
      http_header {
        http_header_name = var.origin_header_name
        values           = [condition.value]
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project}-${var.env}-http-api"
  })
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = "clearpath-api"
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true
      user      = "appuser"

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "ENVIRONMENT", value = var.env },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DB_NAME", value = var.database_name },
        { name = "DB_USER", value = var.database_username },
        { name = "DB_SECRET_ARN", value = var.database_secret_arn },
        { name = "DB_PROXY_ENDPOINT", value = var.rds_proxy_endpoint },
        { name = "GHL_WEBHOOK_SECRET", value = var.ghl_webhook_secret_arn },
        { name = "CLEARPATH_API_KEY_SECRET", value = var.api_key_secret_arn }
      ]

      readonlyRootFilesystem = true

      linuxParameters = {
        initProcessEnabled = true
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = "${var.project}-api"
  })
}

resource "aws_ecs_service" "api" {
  name                   = "clearpath-api"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.api.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = false

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "clearpath-api"
    container_port   = 8000
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.webhooks.arn
    container_name   = "clearpath-api"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  health_check_grace_period_seconds = 60

  tags = merge(local.common_tags, {
    Name = "${var.project}-api-${var.env}"
  })
}
