# Cost Estimate

This stack is intended for a short validation run, not continuous idle hosting. Deploy it, capture evidence, and destroy it the same day.

Pricing changes by region, date, architecture, traffic, and free-tier eligibility. Treat this as a planning guide and verify with the AWS Pricing Calculator before any real deployment. This estimate assumes `us-east-1`, low traffic, dev defaults, and a short 2-3 hour validation window.

## Main Cost Drivers

| Service | Why it costs money | Validation posture |
|---|---|---|
| ECS Fargate | Billed while tasks run based on vCPU, memory, OS/architecture, and task duration. | Keep desired count at `2` only during the validation window. |
| Application Load Balancer | Billed for load balancer hours plus capacity usage. | Required for ECS service routing; destroy after validation artifacts are captured. |
| NAT Gateway | Billed hourly plus data processing. | One of the easiest idle costs to forget; destroy the VPC stack after validation. |
| RDS PostgreSQL | Billed for DB instance hours, storage, backups, and I/O/storage features. | `db.t4g.micro`, Single-AZ, teardown-first settings in dev. |
| RDS Proxy | Billed while the proxy exists; also relies on VPC networking. | Kept because it provides ECS-to-PostgreSQL connection pooling. |
| CloudFront | Billed by request/data transfer and optional features. | Low validation traffic should be minimal, but distribution deletion can take time. |
| AWS WAF | Billed by WebACL, rules, and inspected requests. | Provides edge security; destroy with CloudFront. |
| VPC interface endpoints | Billed hourly per endpoint/AZ plus data processing. | Used so private ECS tasks can reach AWS APIs without public IPs. |
| CloudWatch | Logs, metrics, dashboards, and alarms can create small charges. | Keep retention controlled and destroy after evidence capture. |

## Rough Validation Budget

For a 2-3 hour validation run with light traffic, budget for **low single-digit dollars** rather than cents. The exact number depends on current regional pricing, how long CloudFront takes to disable/delete, data transfer, endpoint count, logs, and whether the stack is left running overnight.

The biggest practical risk is forgetting hourly resources:

- NAT Gateway
- ALB
- RDS instance
- RDS Proxy
- ECS tasks
- VPC interface endpoints
- WAF WebACL

## Guardrails

- Run `terraform plan` before apply and review every billable resource.
- Keep `rds_multi_az = false` for the short validation run.
- Keep `rds_deletion_protection = false` and `alb_deletion_protection = false` for ephemeral teardown.
- Keep `rds_skip_final_snapshot = true` for ephemeral teardown.
- Capture evidence immediately after apply.
- Run `scripts/teardown.sh` the same day.
- Verify with AWS Console and CLI that ECS, RDS, CloudFront, NAT, and WAF resources are gone or deleting.

## Production Contrast

For a real production deployment, the cost posture changes intentionally:

- `rds_multi_az = true`
- larger RDS class after load testing
- `rds_deletion_protection = true`
- `rds_skip_final_snapshot = false`
- `alb_deletion_protection = true`
- longer CloudWatch retention and more alarms

That production posture is more resilient but less teardown-friendly. The dev defaults are intentionally cheaper and easier to destroy.

## Pricing References

- [AWS Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/)
- [Amazon RDS for PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [Amazon RDS Proxy pricing](https://aws.amazon.com/rds/proxy/pricing/)
- [NAT Gateway pricing](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)
- [Amazon CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/)
- [AWS WAF pricing](https://aws.amazon.com/waf/pricing/)
