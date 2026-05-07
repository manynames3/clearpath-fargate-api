locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  should_create_validation_records = var.create_certificate && var.route53_zone_id != ""
  should_create_api_record         = var.create_api_record && var.route53_zone_id != "" && var.cloudfront_domain_name != "" && var.cloudfront_hosted_zone_id != ""
  should_create_origin_record      = var.create_origin_record && var.route53_zone_id != "" && var.alb_dns_name != "" && var.alb_zone_id != ""
}

resource "aws_acm_certificate" "api" {
  count = var.create_certificate ? 1 : 0

  domain_name               = var.api_domain_name
  subject_alternative_names = [var.origin_domain_name]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = var.api_domain_name
  })
}

resource "aws_route53_record" "cert_validation" {
  for_each = local.should_create_validation_records ? {
    for dvo in aws_acm_certificate.api[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  zone_id         = var.route53_zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
}

resource "aws_acm_certificate_validation" "api" {
  count = local.should_create_validation_records ? 1 : 0

  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

resource "aws_route53_record" "api" {
  #checkov:skip=CKV2_AWS_23:Alias target is supplied through module variables from the CloudFront distribution output in the root module.
  count = local.should_create_api_record ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = var.cloudfront_domain_name
    zone_id                = var.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "origin" {
  #checkov:skip=CKV2_AWS_23:Alias target is supplied through module variables from the ALB output in the root module.
  count = local.should_create_origin_record ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.origin_domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = false
  }
}
