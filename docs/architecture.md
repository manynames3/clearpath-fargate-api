# Architecture

Clearpath Lead Intelligence API receives GoHighLevel contact webhooks, stores lead/property/follow-up data in RDS PostgreSQL, and serves query and market snapshot endpoints through CloudFront.

GoHighLevel is connected through a Workflow Custom Webhook that posts contact and property fields to `/webhooks/ghl`; see [ghl-integration.md](ghl-integration.md) for payload mapping and webhook authentication.

```mermaid
sequenceDiagram
    participant Client as Client or GHL
    participant R53 as Route53
    participant CF as CloudFront
    participant WAF as AWS WAF
    participant ALB as ALB
    participant ECS as ECS Fargate
    participant Proxy as RDS Proxy
    participant DB as RDS PostgreSQL

    Client->>R53: api.clearpathpropertygroup.com
    R53->>CF: Alias response
    Client->>CF: HTTPS request
    CF->>WAF: Managed rule and rate-limit evaluation
    WAF->>CF: Allow
    alt /api/market/* cache hit
        CF-->>Client: Cached market snapshot
    else cache miss or dynamic endpoint
        CF->>ALB: HTTPS to origin-api hostname
        ALB->>ECS: HTTP on port 8000 inside VPC
        ECS->>Proxy: IAM-auth PostgreSQL connection
        Proxy->>DB: Pooled database connection
        DB-->>ECS: Query result
        ECS-->>ALB: JSON response
        ALB-->>CF: JSON response
        CF-->>Client: JSON response
    end
```

## Security Boundaries

The ALB security group accepts HTTPS only from the AWS-managed CloudFront origin-facing prefix list. ECS accepts port 8000 only from the ALB security group. RDS Proxy accepts PostgreSQL only from ECS, and the database accepts PostgreSQL only from RDS Proxy.

Runtime credentials are fetched from Secrets Manager. Terraform creates the GHL webhook secret container without writing a secret value into state; load the value out-of-band before starting the service.

## Network Architecture

The deployed network is a three-tier VPC in `us-east-1` with two Availability Zones. The public tier handles ingress and controlled egress. The private app tier runs the container workload and RDS Proxy. The private data tier contains PostgreSQL and has no internet default route.

| Tier | us-east-1a | us-east-1b | Resources | Routing |
|---|---|---|---|---|
| VPC | `10.0.0.0/16` | `10.0.0.0/16` | Shared network boundary | VPC Flow Logs enabled |
| Public | `10.0.1.0/24` | `10.0.2.0/24` | ALB, NAT gateway | Internet Gateway route |
| Private app | `10.0.10.0/24` | `10.0.11.0/24` | ECS Fargate, RDS Proxy, VPC endpoints | NAT plus private AWS service endpoints |
| Private data | `10.0.20.0/24` | `10.0.21.0/24` | RDS PostgreSQL | Isolated database route table |

```mermaid
flowchart TB
    internet["Internet clients and GHL"] --> cloudfront["CloudFront + WAF"]
    cloudfront --> alb["Public subnets: ALB"]
    alb --> ecs["Private app subnets: ECS Fargate"]
    ecs --> proxy["Private app subnets: RDS Proxy"]
    proxy --> rds["Private data subnets: RDS PostgreSQL"]
    ecs --> endpoints["VPC endpoints: ECR, CloudWatch, Secrets Manager, S3"]
    ecs --> nat["NAT gateway for controlled egress"]
```

Security group rules mirror the same path:

| Rule | Source | Destination | Port |
|---|---|---|---|
| ALB ingress | CloudFront origin-facing managed prefix list | ALB SG | `443` |
| App ingress | ALB SG | ECS SG | `8000` |
| Proxy ingress | ECS SG | RDS Proxy SG | `5432` |
| Database ingress | RDS Proxy SG | RDS SG | `5432` |
| Runtime AWS APIs | ECS SG | VPC endpoint SG | `443` |

## RDS vs. Aurora Decision Rationale

The current database choice is standard RDS PostgreSQL, not Aurora. Clearpath's present workload is modest: a few webhook writes, lead/property/follow-up joins, and market snapshot reads that are cached by CloudFront. RDS is the more cost-effective fit for this stage because it can run on a small provisioned instance with predictable pricing while still providing managed PostgreSQL, backups, encryption, Secrets Manager integration, and a clean path to production hardening.

The API does not currently need Aurora-level performance. The important path is fast webhook acknowledgement and straightforward relational queries, not high write throughput, global reads, or many read replicas. RDS PostgreSQL is enough for the expected lead volume, especially because `/api/market/*` is cacheable and should not repeatedly hit the database.

For production failover and high availability, the first upgrade would be RDS Multi-AZ. That gives the project a practical availability story without introducing Aurora's extra capacity model and operational surface before there is traffic to justify it. If the API later sees materially higher webhook volume, heavier concurrent lead searches, strict failover targets, or read-scaling requirements, Aurora PostgreSQL would become a reasonable next step.

Autoscaling is the main future tradeoff. Aurora Serverless can scale capacity more dynamically, but the current workload is not spiky enough to justify that complexity or cost. Provisioned RDS is simpler to size, easier to demo, and cheaper for the current stage; Aurora can be reconsidered when scaling or availability requirements outgrow that model.
