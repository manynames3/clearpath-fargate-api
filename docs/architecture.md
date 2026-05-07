# Architecture

Clearpath Lead Intelligence API receives GoHighLevel contact webhooks, stores lead/property/follow-up data in Aurora PostgreSQL, and serves query and market snapshot endpoints through CloudFront.

```mermaid
sequenceDiagram
    participant Client as Client or GHL
    participant R53 as Route53
    participant CF as CloudFront
    participant WAF as AWS WAF
    participant ALB as ALB
    participant ECS as ECS Fargate
    participant Proxy as RDS Proxy
    participant DB as Aurora PostgreSQL

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

The ALB security group accepts HTTPS only from the AWS-managed CloudFront origin-facing prefix list. ECS accepts port 8000 only from the ALB security group. RDS Proxy accepts PostgreSQL only from ECS, and Aurora accepts PostgreSQL only from RDS Proxy.

Runtime credentials are fetched from Secrets Manager. Terraform creates the GHL webhook secret container without writing a secret value into state; load the value out-of-band before starting the service.

## Auto-Pause Caveat

Aurora Serverless v2 scale-to-zero is configured with `min_capacity = 0` and `seconds_until_auto_pause = 300` in dev. RDS Proxy is also required by the architecture, but active proxy connections can prevent an Aurora cluster from pausing. For demos, use teardown or scale ECS to zero to control cost.
