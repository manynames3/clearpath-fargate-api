# Demo Evidence Template

Use this file as the capture checklist for a short-lived AWS demo. Replace each placeholder with a screenshot path, command output, or short note after deployment. Destroy the stack after evidence is captured.

## Summary

- Demo date:
- Git commit:
- Terraform plan summary:
- Terraform apply summary:
- Terraform destroy summary:
- Total demo window:

## Architecture Evidence

| Area | Evidence | Notes |
|---|---|---|
| Terraform plan | `screenshots/terraform-plan.png` | Show resources to create before apply. |
| ECS service | `screenshots/ecs-service.png` | Desired and running task counts match. |
| ECS task definition | `screenshots/ecs-task-definition.png` | Environment variables use ARNs/endpoints, not plaintext secrets. |
| ALB target health | `screenshots/alb-target-health.png` | Targets healthy on `/health`. |
| RDS PostgreSQL | `screenshots/rds-instance.png` | Private database, encrypted storage, IAM auth enabled. |
| RDS Proxy | `screenshots/rds-proxy-targets.png` | Proxy target registered and available. |
| Security groups | `screenshots/security-groups.png` | CloudFront -> ALB -> ECS -> RDS Proxy -> RDS. |
| CloudFront | `screenshots/cloudfront-distribution.png` | Distribution deployed with API aliases. |
| WAF | `screenshots/waf-web-acl.png` | WebACL attached to CloudFront. |
| CloudWatch | `screenshots/cloudwatch-dashboard.png` | ECS, ALB, CloudFront, and RDS widgets visible. |

## API Evidence

```bash
curl -f https://api.clearpathpropertygroup.com/health
```

Expected:

```json
{"status":"ok","service":"clearpath-api"}
```

```bash
curl -i https://api.clearpathpropertygroup.com/api/market/gwinnett
```

Expected headers:

```text
cache-control: public, max-age=3600
```

Second request should show a CloudFront cache hit when the distribution has warmed.

## Interview Notes

- RDS was selected for the implemented build because current volume is modest and predictable.
- RDS Proxy remains valuable because ECS/Fargate tasks can create many short-lived database connections.
- RDS Multi-AZ is the first production availability upgrade.
- Aurora PostgreSQL is the future option when read scaling, stricter failover, or more dynamic capacity scaling is justified.
- The stack is intentionally teardown-first to avoid idle ECS, ALB, NAT, RDS, RDS Proxy, CloudFront, and WAF cost.

## Teardown Evidence

```bash
scripts/teardown.sh
```

Capture:

- ECS service scaled to zero before destroy
- Terraform destroy plan reviewed
- Terraform destroy completed
- RDS instances no longer listed
- CloudFront distribution no longer listed or disabled/deleting
