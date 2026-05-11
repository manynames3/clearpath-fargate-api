# Live Validation Screenshots

These screenshots are public-safe crops from the short-lived AWS validation run completed on 2026-05-10. They are intentionally cropped or redacted to avoid publishing account metadata, full ARNs, private network identifiers, generated secret names, or Secrets Manager ARNs.

## Runtime Path

| File | Shows |
|---|---|
| `01-cloudfront-health-response.png` | API `/health` response through CloudFront |
| `02-ecs-cluster-running.png` | ECS cluster active with two running tasks |
| `03-ecs-service-healthy-tasks.png` | ECS service deployment success and healthy tasks |
| `04-fargate-task-configuration.png` | Fargate launch type, CPU/memory, and task roles |
| `05-alb-active.png` | ALB active and internet-facing |
| `06-alb-target-groups.png` | Separate API and webhook target groups |
| `07-api-target-group-healthy.png` | API target group health |
| `08-webhook-target-group-healthy.png` | Webhook target group health |

## Edge, Security, And Data

| File | Shows |
|---|---|
| `09-cloudfront-waf-attached.png` | WAF enabled on CloudFront |
| `10-cloudfront-distribution-settings.png` | CloudFront distribution settings |
| `11-waf-dashboard-traffic.png` | WAF dashboard traffic view |
| `12-rds-postgresql-available.png` | RDS PostgreSQL instance available |
| `13-rds-proxy-target-group.png` | RDS Proxy target group attached to PostgreSQL |
| `14-vpc-resource-map.png` | VPC subnets, route tables, NAT, IGW, and S3 endpoint |
| `15-cloudwatch-alarms-ok.png` | CloudWatch alarms in OK state |
| `16-ecs-cloudwatch-metrics.png` | ECS CPU and memory metrics |
| `17-ecr-repository-kms-encryption.png` | ECR repository with KMS encryption |
| `18-kms-customer-managed-keys.png` | Customer-managed KMS keys used by the stack |

Raw screenshots from the validation run are not committed because they contain AWS account IDs, full ARNs, generated endpoint names, and secret references.
