# Architecture Decision Records

These records document the main infrastructure and platform decisions for Clearpath Lead Intelligence API.

| ADR | Decision |
|---|---|
| [0001](0001-use-ecs-fargate-for-api.md) | Use ECS Fargate for the API runtime |
| [0002](0002-use-rds-postgresql-for-current-workload.md) | Use RDS PostgreSQL for the current relational workload |
| [0003](0003-use-rds-proxy-for-database-connections.md) | Use RDS Proxy between ECS and PostgreSQL |
| [0004](0004-place-cloudfront-and-waf-before-alb.md) | Place CloudFront and WAF before the ALB |
| [0005](0005-keep-kubernetes-as-optional-platform-track.md) | Keep Kubernetes as an optional platform track |
| [0006](0006-use-postgresql-for-lead-intelligence.md) | Use PostgreSQL as the lead intelligence source of truth |
