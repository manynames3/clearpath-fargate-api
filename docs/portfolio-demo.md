# Portfolio Demo

This project should be deployed only long enough to capture evidence, then destroyed. The cost-aware design choice is part of the portfolio story: RDS PostgreSQL is implemented for the current workload because it is cheaper and simpler than Aurora, while Aurora remains a documented upgrade path.

## Interview Positioning

Use this framing:

> I considered Aurora Serverless v2, but chose RDS PostgreSQL for the implemented build because the expected workload is modest: webhook writes, lead lookups, and cached market reads. RDS gives the project managed PostgreSQL, backups, encryption, IAM auth, Secrets Manager integration, and a clear Multi-AZ production path at lower cost. Aurora is documented as the next step if traffic, read scaling, or failover requirements increase.

That answer shows practical AWS judgment: use the right managed service for the workload, not the most expensive one by default.

## Short-Lived AWS Demo

Run this only when ready to spend a small amount for screenshots and validation. Always review the plan before apply.
Read [cost-estimate.md](cost-estimate.md) before starting the demo window.

```bash
cd terraform/environments/dev
terraform plan -out=tfplan
terraform apply tfplan
```

After apply, capture:

- Terraform apply summary
- ECS cluster and service with healthy task count
- ECS task definition showing environment variables sourced from ARNs, not plaintext secrets
- ALB target group health checks passing
- RDS PostgreSQL instance private/public accessibility settings
- RDS Proxy target health
- Security groups showing CloudFront to ALB to ECS to RDS Proxy to RDS
- CloudFront distribution deployed
- WAF WebACL attached to CloudFront
- CloudWatch dashboard and alarms
- API health response through the custom domain
- `/api/market/gwinnett` response with cache headers

Use [demo-evidence-template.md](demo-evidence-template.md) as the screenshot and command-output checklist. Store screenshots in `docs/screenshots/`.

Then destroy the stack the same day.

```bash
cd ../../..
scripts/teardown.sh
```

If using manual commands instead of the teardown script, follow [teardown.md](teardown.md).

## Production Hardening Notes

The demo defaults prioritize cost and clean teardown. For a real production deployment:

- use `terraform/environments/dev/production.tfvars.example` as the starting override file
- enable RDS Multi-AZ
- increase the RDS instance class after load testing
- set `rds_deletion_protection = true`
- set `rds_skip_final_snapshot = false` and provide `rds_final_snapshot_identifier`
- set `alb_deletion_protection = true`
- preserve SSL enforcement with `rds.force_ssl = 1`
- keep RDS Proxy between ECS and PostgreSQL
- tune ECS desired count and autoscaling from observed request volume
- keep CloudFront caching on market snapshots

Aurora PostgreSQL is the future upgrade path when workload patterns justify it: high concurrency, read replica needs, stricter failover goals, or more dynamic capacity scaling.
