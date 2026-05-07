project    = "clearpath-api"
env        = "dev"
aws_region = "us-east-1"

vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

public_subnet_cidrs           = ["10.0.1.0/24", "10.0.2.0/24"]
private_ecs_subnet_cidrs      = ["10.0.10.0/24", "10.0.11.0/24"]
private_database_subnet_cidrs = ["10.0.20.0/24", "10.0.21.0/24"]

database_name                = "clearpath"
master_username              = "clearpath_admin"
postgres_engine_version      = "15.7"
rds_instance_class           = "db.t4g.micro"
rds_allocated_storage_gb     = 20
rds_max_allocated_storage_gb = 100
rds_multi_az                 = false
rds_deletion_protection      = false
rds_skip_final_snapshot      = true

app_database_username   = "clearpath_app"
ecr_repository_name     = "clearpath/api"
ecs_log_group_name      = "/ecs/clearpath-api"
ecs_desired_count       = 2
alb_deletion_protection = false

api_domain_name    = "api.clearpathpropertygroup.com"
origin_domain_name = "origin-api.clearpathpropertygroup.com"

# Empty keeps Route53 records out of local-only plans. Set to the hosted zone ID before applying.
route53_zone_id = ""
