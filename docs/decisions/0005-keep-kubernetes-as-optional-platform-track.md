# ADR 0005: Keep Kubernetes as an Optional Platform Track

Date: 2026-05-08

Status: Accepted

## Context

The API can run as a standard container. ECS Fargate is the primary AWS deployment path, but some teams standardize on Kubernetes for workloads, rollout controls, network policies, autoscaling, and platform-level consistency.

The main alternatives considered were making EKS the primary deployment path or omitting Kubernetes manifests entirely.

## Decision

Keep ECS Fargate as the primary AWS path and maintain Kubernetes manifests as an optional platform track under `k8s/`.

## Rationale

ECS Fargate is simpler and more cost-effective for the current single-service AWS deployment. It integrates directly with the Terraform modules, ALB target groups, task roles, CloudWatch logs, RDS Proxy, and Secrets Manager.

Kubernetes manifests are still valuable because they define a portable runtime shape: Deployment, Service, ServiceAccount, ConfigMap, readiness/liveness probes, HPA, PDB, NetworkPolicy, and an EKS overlay.

Making EKS primary would add control plane cost, IAM integration complexity, cluster operations, and controller dependencies that are not required for this standalone API.

## Consequences

- The `k8s/` directory remains source-only until an EKS validation run is intentional.
- Local Kubernetes validation can use the `local` overlay with kind or minikube.
- The EKS overlay requires real AWS values for ECR, RDS Proxy, Secrets Manager, and pod IAM before deployment.
- ECS and Kubernetes configuration must stay aligned on health checks, environment variables, and secret references.
