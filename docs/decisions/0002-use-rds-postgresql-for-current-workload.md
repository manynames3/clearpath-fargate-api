# ADR 0002: Use RDS PostgreSQL for the Current Relational Workload

Date: 2026-05-08

Status: Accepted

## Context

The API stores leads, properties, follow-ups, and market snapshots. The access pattern is relational: lead queries join contact data, property details, and last follow-up state. Market snapshot reads are cacheable through CloudFront.

The main alternatives considered were DynamoDB and Aurora PostgreSQL.

## Decision

Use standard RDS PostgreSQL for the current implementation.

## Rationale

PostgreSQL is a good fit for the data model because the application benefits from joins, indexes, unique constraints, and SQL query flexibility. RDS PostgreSQL provides managed backups, encryption, parameter groups, Secrets Manager integration, IAM authentication support, and a direct path to Multi-AZ production hardening.

DynamoDB is not the right primary datastore for this workflow because the core queries are relational and would require denormalization or multiple query-specific item shapes.

Aurora PostgreSQL remains a reasonable future option, but it is more capacity and operational surface than the current workload needs. The expected volume is modest: webhook writes, lead searches, and cached market snapshot reads. RDS keeps cost and sizing predictable while preserving the relational design.

## Consequences

- The dev environment uses a small provisioned RDS instance.
- Production hardening should enable Multi-AZ, deletion protection, final snapshots, and a larger instance class after load testing.
- Aurora can be reconsidered if webhook volume, read scaling, failover targets, or concurrency requirements outgrow provisioned RDS.
- RDS Proxy remains part of the design to protect PostgreSQL from task-level connection pressure.
