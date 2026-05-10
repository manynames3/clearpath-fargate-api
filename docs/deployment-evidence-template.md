# Deployment Evidence Template

Use this file as the capture checklist for a short-lived AWS validation run. Replace each placeholder with a screenshot path, command output, or short note after deployment. Store screenshots in `docs/screenshots/`. Destroy the stack after evidence is captured.

## Summary

- Validation date:
- Git commit:
- AWS region:
- Terraform workspace/backend:
- Terraform plan summary:
- Terraform apply summary:
- Terraform destroy summary:
- Total validation window:
- Estimated validation cost:
- API base URL from Terraform:

```bash
export API_BASE_URL="$(terraform -chdir=terraform/environments/dev output -raw api_base_url)"
```

## Architecture Evidence

| Area | Evidence | Notes |
|---|---|---|
| Terraform plan | `docs/screenshots/terraform-plan.png` | Show resources to create before apply. |
| Terraform apply | `docs/screenshots/terraform-apply.png` | Show successful apply and key outputs. |
| VPC | `docs/screenshots/vpc.png` | VPC `10.0.0.0/16`, tags, and Flow Logs. |
| Subnets | `docs/screenshots/subnets.png` | Six subnets across `us-east-1a` and `us-east-1b`. |
| Route tables | `docs/screenshots/route-tables.png` | Public IGW route, private app NAT route, isolated database route table. |
| VPC endpoints | `docs/screenshots/vpc-endpoints.png` | ECR, CloudWatch Logs, Secrets Manager, and S3 endpoints for private tasks. |
| Security groups | `docs/screenshots/security-groups.png` | CloudFront -> ALB -> ECS -> RDS Proxy -> RDS. |
| ECS service | `docs/screenshots/ecs-service.png` | Desired and running task counts match. |
| ECS task definition | `docs/screenshots/ecs-task-definition.png` | Environment variables use ARNs/endpoints, not plaintext secrets. |
| ECS logs | `docs/screenshots/cloudwatch-logs.png` | Container startup and health-check logs visible. |
| ALB target health | `docs/screenshots/alb-target-health.png` | Targets healthy on `/health`. |
| RDS PostgreSQL | `docs/screenshots/rds-instance.png` | Private database, encrypted storage, IAM auth enabled. |
| RDS Proxy | `docs/screenshots/rds-proxy-targets.png` | Proxy target registered and available. |
| CloudFront | `docs/screenshots/cloudfront-distribution.png` | Distribution deployed with generated domain, or API aliases if custom-domain mode is enabled. |
| WAF | `docs/screenshots/waf-web-acl.png` | WebACL attached to CloudFront. |
| CloudWatch | `docs/screenshots/cloudwatch-dashboard.png` | ECS, ALB, CloudFront, and RDS widgets visible. |

## API Evidence

```bash
curl -f "$API_BASE_URL/health"
```

Expected:

```json
{"status":"ok","service":"clearpath-api"}
```

```bash
curl -f "$API_BASE_URL/ready"
```

Expected:

```json
{"status":"ready","service":"clearpath-api"}
```

```bash
curl -X POST "$API_BASE_URL/webhooks/ghl" \
  -H "Content-Type: application/json" \
  -H "X-Clearpath-Webhook-Secret: <redacted>" \
  -d '{"id":"validation-ghl-001","firstName":"Validation","lastName":"Lead","status":"warm","customFields":[{"key":"county","field_value":"Gwinnett"},{"key":"property_address","field_value":"25 Validation Ridge"}]}'
```

Expected:

```json
{"status":"accepted","lead_id":"<uuid>"}
```

```bash
curl -f "$API_BASE_URL/api/leads?county=Gwinnett&status=warm" \
  -H "X-Clearpath-API-Key: <redacted>"
```

Expected: the webhook lead appears with property data.

```bash
curl -i "$API_BASE_URL/api/market/gwinnett"
```

Expected headers:

```text
cache-control: public, max-age=3600
```

Second request should show a CloudFront cache hit when the distribution has warmed.

## AWS CLI Evidence

Run these from the same commit and capture command output as text or screenshots.

The same read-only checks can be collected automatically:

```bash
make deployment-evidence
```

```bash
aws ec2 describe-vpcs --filters Name=tag:Project,Values=clearpath-api
aws ec2 describe-subnets --filters Name=tag:Project,Values=clearpath-api
aws ec2 describe-security-groups --filters Name=tag:Project,Values=clearpath-api
```

```bash
aws ecs describe-services \
  --cluster clearpath-dev \
  --services clearpath-api \
  --query 'services[0].{Running:runningCount,Desired:desiredCount,Status:status}'
```

```bash
aws rds describe-db-instances \
  --query 'DBInstances[?DBName==`clearpath`].{ID:DBInstanceIdentifier,Public:PubliclyAccessible,Encrypted:StorageEncrypted,Status:DBInstanceStatus}'
```

```bash
aws rds describe-db-proxies \
  --db-proxy-name clearpath-proxy-dev \
  --query 'DBProxies[0].{Name:DBProxyName,Status:Status,RequireTLS:RequireTLS}'
```

```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[?Comment==`clearpath-api`].{Domain:DomainName,Status:Status}'
```

## Design Notes

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
- ECR images intentionally retained or removed
- RDS instances no longer listed
- CloudFront distribution no longer listed or disabled/deleting
- NAT gateway and ALB no longer listed
