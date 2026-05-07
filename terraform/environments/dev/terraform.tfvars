project    = "clearpath-api"
env        = "dev"
aws_region = "us-east-1"

vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

public_subnet_cidrs         = ["10.0.1.0/24", "10.0.2.0/24"]
private_ecs_subnet_cidrs    = ["10.0.10.0/24", "10.0.11.0/24"]
private_aurora_subnet_cidrs = ["10.0.20.0/24", "10.0.21.0/24"]

database_name         = "clearpath"
master_username       = "clearpath_admin"
aurora_engine_version = "15.7"

# Aurora Serverless v2 scale-to-zero requires min capacity 0 and a compatible engine version.
aurora_min_capacity       = 0
aurora_max_capacity       = 4
aurora_auto_pause_seconds = 300

app_database_username = "clearpath_app"
ecr_repository_name   = "clearpath/api"
ecs_log_group_name    = "/ecs/clearpath-api"
ecs_desired_count     = 2

api_domain_name    = "api.clearpathpropertygroup.com"
origin_domain_name = "origin-api.clearpathpropertygroup.com"

# Empty keeps Route53 records out of local-only plans. Set to the hosted zone ID before applying.
route53_zone_id = ""
