locals {
  common_tags = {
    Project     = var.project
    Environment = var.env
    ManagedBy   = "terraform"
  }

  custom_domain_enabled         = var.use_custom_domain && var.route53_zone_id != ""
  cloudfront_origin_domain_name = local.custom_domain_enabled ? var.origin_domain_name : module.ecs.alb_dns_name
  cloudfront_origin_protocol    = local.custom_domain_enabled ? "https-only" : "http-only"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}

module "networking" {
  source = "../../modules/networking"

  project                       = var.project
  env                           = var.env
  aws_region                    = var.aws_region
  vpc_cidr                      = var.vpc_cidr
  availability_zones            = var.availability_zones
  public_subnet_cidrs           = var.public_subnet_cidrs
  private_ecs_subnet_cidrs      = var.private_ecs_subnet_cidrs
  private_database_subnet_cidrs = var.private_database_subnet_cidrs
}

module "dns_certificate" {
  source = "../../modules/dns"

  providers = {
    aws = aws.us_east_1
  }

  project              = var.project
  env                  = var.env
  api_domain_name      = var.api_domain_name
  origin_domain_name   = var.origin_domain_name
  route53_zone_id      = var.route53_zone_id
  create_certificate   = local.custom_domain_enabled
  create_api_record    = false
  create_origin_record = false
}

module "rds" {
  source = "../../modules/rds"

  project                   = var.project
  env                       = var.env
  aws_region                = var.aws_region
  database_subnet_ids       = module.networking.private_database_subnet_ids
  rds_proxy_subnet_ids      = module.networking.private_ecs_subnet_ids
  database_sg_id            = module.networking.database_sg_id
  rds_proxy_sg_id           = module.networking.rds_proxy_sg_id
  database_name             = var.database_name
  master_username           = var.master_username
  engine_version            = var.postgres_engine_version
  instance_class            = var.rds_instance_class
  allocated_storage_gb      = var.rds_allocated_storage_gb
  max_allocated_storage_gb  = var.rds_max_allocated_storage_gb
  multi_az                  = var.rds_multi_az
  deletion_protection       = var.rds_deletion_protection
  skip_final_snapshot       = var.rds_skip_final_snapshot
  final_snapshot_identifier = var.rds_final_snapshot_identifier
}

module "iam" {
  source = "../../modules/iam"

  project               = var.project
  env                   = var.env
  aws_region            = var.aws_region
  database_secret_arn   = module.rds.master_user_secret_arn
  database_kms_key_arn  = module.rds.database_kms_key_arn
  rds_proxy_resource_id = module.rds.rds_proxy_resource_id
  database_username     = var.app_database_username
  ecr_repository_name   = var.ecr_repository_name
  ecs_log_group_name    = var.ecs_log_group_name
}

module "ecs" {
  source = "../../modules/ecs"

  project                 = var.project
  env                     = var.env
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  public_subnet_ids       = module.networking.public_subnet_ids
  private_subnet_ids      = module.networking.private_ecs_subnet_ids
  alb_sg_id               = module.networking.alb_sg_id
  ecs_sg_id               = module.networking.ecs_sg_id
  ecs_task_role_arn       = module.iam.ecs_task_role_arn
  ecs_execution_role_arn  = module.iam.ecs_execution_role_arn
  ecr_repository_name     = var.ecr_repository_name
  ecs_log_group_name      = var.ecs_log_group_name
  database_name           = var.database_name
  database_username       = var.app_database_username
  database_secret_arn     = module.rds.master_user_secret_arn
  rds_proxy_endpoint      = module.rds.rds_proxy_endpoint
  ghl_webhook_secret_arn  = module.iam.ghl_webhook_secret_arn
  api_key_secret_arn      = module.iam.api_key_secret_arn
  acm_cert_arn            = local.custom_domain_enabled ? module.dns_certificate.certificate_arn : ""
  create_https_listener   = local.custom_domain_enabled
  create_http_listener    = !local.custom_domain_enabled
  desired_count           = var.ecs_desired_count
  alb_deletion_protection = var.alb_deletion_protection
  origin_header_name      = var.origin_header_name
  origin_header_value     = var.origin_header_value
}

module "cloudfront" {
  source = "../../modules/cloudfront"

  providers = {
    aws = aws.us_east_1
  }

  project             = var.project
  env                 = var.env
  api_domain_name     = var.api_domain_name
  origin_domain_name  = local.cloudfront_origin_domain_name
  origin_protocol     = local.cloudfront_origin_protocol
  use_custom_domain   = local.custom_domain_enabled
  acm_cert_arn        = local.custom_domain_enabled ? module.dns_certificate.certificate_arn : ""
  origin_header_name  = var.origin_header_name
  origin_header_value = var.origin_header_value
}

module "dns_records" {
  source = "../../modules/dns"

  providers = {
    aws = aws.us_east_1
  }

  project                   = var.project
  env                       = var.env
  api_domain_name           = var.api_domain_name
  origin_domain_name        = var.origin_domain_name
  route53_zone_id           = var.route53_zone_id
  create_certificate        = false
  create_api_record         = local.custom_domain_enabled
  create_origin_record      = local.custom_domain_enabled
  cloudfront_domain_name    = module.cloudfront.distribution_domain_name
  cloudfront_hosted_zone_id = module.cloudfront.distribution_hosted_zone_id
  alb_dns_name              = module.ecs.alb_dns_name
  alb_zone_id               = module.ecs.alb_zone_id
}

module "observability" {
  source = "../../modules/observability"

  project                     = var.project
  env                         = var.env
  aws_region                  = var.aws_region
  ecs_cluster_name            = module.ecs.cluster_name
  ecs_service_name            = module.ecs.service_name
  alb_arn_suffix              = module.ecs.alb_arn_suffix
  api_target_group_arn_suffix = module.ecs.api_target_group_arn_suffix
  cloudfront_distribution_id  = module.cloudfront.distribution_id
  db_instance_identifier      = module.rds.db_instance_identifier
}
