# Clearpath Lead Intelligence API

[![Build and Deploy](https://github.com/manynames3/clearpath-fargate-api/actions/workflows/build-push.yml/badge.svg)](https://github.com/manynames3/clearpath-fargate-api/actions/workflows/build-push.yml)
[![Terraform Validate](https://github.com/manynames3/clearpath-fargate-api/actions/workflows/terraform-validate.yml/badge.svg)](https://github.com/manynames3/clearpath-fargate-api/actions/workflows/terraform-validate.yml)

Containerized REST API on ECS Fargate, RDS PostgreSQL, RDS Proxy, CloudFront, Route53, WAF, and Secrets Manager.

This repository is built as a production-pattern AWS Terraform project for Clearpath Property Group's off-market real estate lead workflow. It is intentionally small at the application layer: the infrastructure is the story. ECS Fargate is the primary AWS deployment path, with an optional Kubernetes/EKS manifest track in `k8s/`.

## Deployment Status

This repo is currently built and validated locally only. Do not run `terraform apply` until you intentionally want to create billable AWS resources.

## Ephemeral Deployment Strategy

This project is designed to be deployed briefly, documented, and destroyed. The architectural value is the Terraform implementation and service design, not leaving ECS, ALB, RDS, RDS Proxy, NAT, CloudFront, and WAF running at idle.

The main database tradeoff is cost-aware and workload-driven: RDS PostgreSQL is implemented because the current workload is modest and predictable, while Aurora is documented as the upgrade path for higher scale or availability requirements.

During an intentional AWS validation run, capture the operational artifacts, then tear the stack down:

- ECS service with healthy Fargate tasks
- ALB target group health
- RDS PostgreSQL instance in private subnets
- RDS Proxy target healthy
- CloudFront distribution with WAF attached
- `/api/market/*` cache behavior or response headers
- CloudWatch dashboard and alarms
- Terraform plan/apply/destroy output

See [docs/deployment-validation.md](docs/deployment-validation.md) for the short-lived deployment checklist.
Use [docs/deployment-evidence-template.md](docs/deployment-evidence-template.md) when capturing screenshots and command output.
Review [docs/cost-estimate.md](docs/cost-estimate.md) before applying in AWS.
Review [docs/kubernetes.md](docs/kubernetes.md) for the Kubernetes/EKS track.
Use [docs/ghl-integration.md](docs/ghl-integration.md) for the GoHighLevel webhook setup and payload mapping.

## Local Quick Start

The fastest local run is Docker Compose: FastAPI plus Postgres, no AWS resources.

```bash
cp .env.example .env
make dev-detached
make seed
make smoke
```

Open:

- `http://localhost:8000/health`
- `http://localhost:8000/api/leads?county=Gwinnett&limit=5`
- `http://localhost:8000/api/market/gwinnett`

Stop and remove local containers:

```bash
make clean
```

If Docker is not installed, use the SQLite fallback:

```bash
make install
make seed-local
make dev-local
```

Then run the same `localhost:8000` API calls.

## Sample API Calls

```bash
curl -f http://localhost:8000/health
```

```bash
curl -f "http://localhost:8000/api/leads?county=Gwinnett&limit=5"
```

```bash
curl -f "http://localhost:8000/api/market/gwinnett"
```

```bash
curl -X POST http://localhost:8000/webhooks/ghl \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "sample-webhook-001",
    "first_name": "Jordan",
    "last_name": "Carter",
    "phone": "+14045550199",
    "source": "sms",
    "status": "warm",
    "custom_fields": {
      "property_address": "25 Sample Ridge",
      "city": "Lawrenceville",
      "county": "Gwinnett",
      "state": "GA",
      "situation": "inherited"
    }
  }'
```

## Why This Architecture

| Service | Why not the alternative |
|---|---|
| ECS Fargate | GHL webhooks need warm, predictable responses. Lambda in a VPC can introduce cold-start latency, and future scoring jobs may exceed Lambda's runtime model. |
| RDS PostgreSQL | Lead, property, and follow-up data is relational and benefits from joins. DynamoDB is not the right primary shape for this workflow, and Aurora is more capacity than the current workload needs. |
| RDS Proxy | Fargate tasks create database connections; the proxy pools and protects the database from connection pressure. |
| CloudFront | Market snapshot responses are cacheable and should not hit Fargate or the database on every read. |
| Route53 | Provides real API and origin DNS routing for the CloudFront and ALB path. |
| ALB | Routes `/api/*`, `/webhooks/*`, and `/health` to ECS targets and terminates TLS at the regional origin. |
| Secrets Manager | RDS-managed database credentials and webhook HMAC secrets stay out of code and Terraform variable values. |
| WAF | AWS managed rules and webhook rate limiting protect the CloudFront edge. |
| Kubernetes/EKS manifests | Included as an optional platform track for portable container operations. ECS remains the cost-controlled AWS deployment path. |

## RDS vs. Aurora Decision Rationale

This project currently uses standard RDS PostgreSQL because the expected workload is small and predictable: webhook ingestion, lead lookups, and cached county-level market reads. For this stage, RDS is the more cost-effective choice than Aurora because it can run on a modest provisioned instance, avoids Aurora capacity overhead, and still provides the relational database features the API needs.

The performance requirement is practical rather than extreme. The API needs fast responses for GoHighLevel webhooks and simple joined lead queries, but it does not yet need Aurora's distributed storage layer, read replicas, or high-throughput autoscaling. CloudFront also absorbs repeat traffic for `/api/market/*`, which reduces pressure on the application and database.

For production failover and high availability, RDS can be promoted to Multi-AZ when the project has real uptime requirements. That is a straightforward upgrade path without taking on Aurora-specific operational behavior too early. Aurora would make more sense later if lead volume grows materially, concurrent webhook traffic increases, read scaling becomes necessary, or the business needs stronger regional availability and faster failover characteristics.

Autoscaling is another tradeoff. Aurora Serverless can scale capacity more dynamically, but this API does not currently have spiky enough database demand to justify that complexity. A small provisioned RDS instance is easier to reason about, easier to estimate for short validation runs, and cheaper for the expected volume. The project can revisit Aurora when traffic, scaling, or availability requirements are no longer served well by provisioned RDS.

## Production Upgrade Path

The default dev settings are intentionally cost-controlled. For a real production launch, keep the same service boundaries but harden the database and teardown settings:

- use `terraform/environments/dev/production.tfvars.example` as the starting override file
- set `rds_multi_az = true`
- choose a larger RDS class after load testing, such as `db.t4g.small` or `db.t4g.medium`
- set `rds_deletion_protection = true`
- set `rds_skip_final_snapshot = false` and provide `rds_final_snapshot_identifier`
- set `alb_deletion_protection = true`
- keep `rds.force_ssl = 1`
- keep RDS Proxy for Fargate connection pooling
- add alarms for CPU, storage, connections, latency, and free memory

Aurora PostgreSQL becomes the next database option if webhook volume, concurrent lead searches, read scaling, or failover requirements outgrow provisioned RDS.

## Architecture

```mermaid
flowchart LR
    client["GHL / API client"] --> r53["Route53 api.clearpathpropertygroup.com"]
    r53 --> cf["CloudFront"]
    cf --> waf["AWS WAF WebACL"]
    waf --> origin["origin-api.clearpathpropertygroup.com"]
    origin --> alb["ALB HTTPS listener"]
    alb --> ecs["ECS Fargate clearpath-api"]
    ecs --> proxy["RDS Proxy"]
    proxy --> db["RDS PostgreSQL"]
    ecs --> secrets["Secrets Manager"]
    ecs --> logs["CloudWatch Logs"]
```

## Network Architecture

The Terraform networking module builds a three-tier VPC in `us-east-1` across two Availability Zones. Public subnets only host internet-facing entry infrastructure. ECS tasks and RDS Proxy stay in private app subnets, and PostgreSQL stays in private database subnets with no default route to the internet.

| Tier | us-east-1a | us-east-1b | Resources | Routing |
|---|---|---|---|---|
| VPC | `10.0.0.0/16` | `10.0.0.0/16` | Shared network boundary | Tagged and flow-logged |
| Public | `10.0.1.0/24` | `10.0.2.0/24` | ALB, NAT gateway | `0.0.0.0/0` to Internet Gateway |
| Private app | `10.0.10.0/24` | `10.0.11.0/24` | ECS Fargate tasks, RDS Proxy, VPC endpoints | NAT for controlled egress; S3 and interface endpoints for AWS services |
| Private data | `10.0.20.0/24` | `10.0.21.0/24` | RDS PostgreSQL | Isolated route table, no internet default route |

Security group flow is intentionally narrow:

| From | To | Port | Control |
|---|---|---|---|
| CloudFront origin-facing prefix list | ALB | `443` | ALB does not accept arbitrary internet sources |
| ALB security group | ECS security group | `8000` | App traffic only from the load balancer |
| ECS security group | RDS Proxy security group | `5432` | Application connects through the proxy only |
| RDS Proxy security group | RDS security group | `5432` | Database accepts PostgreSQL only from RDS Proxy |
| ECS security group | VPC endpoint security group | `443` | Private access to AWS APIs used at runtime |

## Endpoints

- `POST /webhooks/ghl` - GoHighLevel contact webhook ingestion
- `GET /api/leads?county=Gwinnett&status=warm&days_since_contact=30`
- `GET /api/market/gwinnett`
- `GET /health`

## Local Validation

```bash
make validate
```

Equivalent individual commands:

```bash
.venv/bin/pytest app/tests
terraform -chdir=terraform/environments/dev init -backend=false
terraform -chdir=terraform/environments/dev validate
.venv/bin/checkov -d terraform/ --framework terraform --quiet
```

## Apply Gate

The intended workflow is always:

```bash
terraform -chdir=terraform/environments/dev plan -out=tfplan
terraform -chdir=terraform/environments/dev apply tfplan
```

Do not skip the plan review. Set `route53_zone_id` in `terraform/environments/dev/terraform.tfvars` before applying DNS/ACM resources.

## Deployment Validation Artifacts

When validating the stack in AWS, capture artifacts that show the build ran end to end:

| Evidence | What to show |
|---|---|
| Terraform plan/apply | Reviewed plan, successful apply, and outputs for ALB, CloudFront, RDS Proxy, and domains |
| Network | VPC, six subnets across two AZs, route tables, NAT gateway, VPC endpoints, and VPC Flow Logs |
| Security groups | CloudFront to ALB, ALB to ECS, ECS to RDS Proxy, RDS Proxy to RDS |
| ECS/Fargate | Cluster, service, two running tasks, task definition, and CloudWatch logs |
| Database | RDS PostgreSQL private accessibility, encryption, Secrets Manager integration, and RDS Proxy healthy target |
| Edge | CloudFront distribution deployed, WAF attached, custom domain behavior, and `/api/market/*` cache hit |
| API | `/health`, `/webhooks/ghl`, `/api/leads`, and `/api/market/gwinnett` responses through the deployed domain |
| Teardown | ECS scaled down, Terraform destroy completed, and billable resources removed |

After apply, collect read-only CLI evidence with:

```bash
make deployment-evidence
```

## Cost Profile

The stack is designed for short validation windows and teardown. RDS is the current database target because it keeps costs predictable while preserving a realistic relational architecture. For cost control, scale ECS to zero before validation ends or destroy the stack.

| Service | Approximate cost driver |
|---|---|
| ECS Fargate | 2 small always-on tasks while deployed |
| RDS PostgreSQL | Small provisioned database instance while deployed |
| RDS Proxy | Hourly proxy capacity |
| ALB | Hourly load balancer cost |
| CloudFront/WAF | Low traffic request and rule processing cost |

Validation screenshots should be stored under `docs/screenshots/` after AWS validation. Do not keep the stack running just to preserve images.

## CI/CD

GitHub Actions validates app tests and Terraform. Deployment is manual-gated with `workflow_dispatch` so a normal push cannot accidentally push an image or roll ECS.

GitLab CI mirrors Terraform validation for CI coverage.
