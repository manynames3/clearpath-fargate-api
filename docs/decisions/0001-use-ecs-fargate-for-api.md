# ADR 0001: Use ECS Fargate for the API Runtime

Date: 2026-05-08

Status: Accepted

## Context

Clearpath Lead Intelligence API receives GoHighLevel contact webhook events and serves lead and market snapshot endpoints. The application is intentionally small, but it needs a stable container runtime, private VPC networking, load balancer integration, CloudWatch logging, and IAM access to Secrets Manager and RDS Proxy.

The main alternatives considered were AWS Lambda and Kubernetes/EKS.

## Decision

Use ECS Fargate as the primary AWS runtime for the FastAPI container.

## Rationale

ECS Fargate fits a single-service container API with low operational overhead. It supports private subnet placement, ALB target groups, task roles, managed deployments, health checks, and CloudWatch logs without requiring EC2 capacity management.

Lambda would reduce always-on compute cost, but this API already uses a container image, RDS Proxy, and VPC-integrated database access. Lambda can work for similar APIs, but VPC cold-start behavior and connection management are less direct for this workload.

EKS would provide Kubernetes-native operations, but it adds control plane cost and cluster management that are not necessary for this standalone API.

## Consequences

- ECS tasks run as private Fargate tasks with no public IPs.
- ALB health checks and ECS deployment circuit breakers are the main runtime safety controls.
- Task execution and task IAM roles must remain least-privilege.
- RDS Proxy remains important because the service can scale task count and connection count independently.
- Kubernetes manifests are maintained separately as an optional portability track.
