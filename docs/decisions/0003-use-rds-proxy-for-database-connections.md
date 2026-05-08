# ADR 0003: Use RDS Proxy for Database Connections

Date: 2026-05-08

Status: Accepted

## Context

The API runs on ECS Fargate, and each task can open database connections. As task count changes or deployments roll, direct database connections can spike. PostgreSQL connection limits are finite, especially on small instance classes used by cost-controlled dev environments.

The main alternatives considered were direct application-to-RDS connections and application-only pooling.

## Decision

Use RDS Proxy between ECS Fargate tasks and RDS PostgreSQL.

## Rationale

RDS Proxy pools and reuses database connections across application tasks. It reduces the risk of connection storms during ECS deployments, restarts, and task scaling. It also keeps database authentication integrated with Secrets Manager and IAM.

Application-level pooling is still useful, but it only manages connections inside each task. It does not coordinate connection pressure across all running tasks.

Direct connections would be simpler, but they couple task scaling directly to PostgreSQL connection count.

## Consequences

- ECS connects to the proxy endpoint, not directly to the database endpoint.
- Security groups enforce ECS to RDS Proxy to RDS as the only database path.
- IAM policies must allow the task role to connect only as the intended database user.
- The proxy is an additional billable resource and should be destroyed with the rest of the stack after validation.
