# ADR 0004: Place CloudFront and WAF Before the ALB

Date: 2026-05-08

Status: Accepted

## Context

The API exposes dynamic lead and webhook endpoints plus a cacheable market snapshot endpoint. The public entry path should support TLS, edge caching, managed web application firewall rules, and protection against direct access to the regional origin where practical.

The main alternatives considered were exposing the ALB directly or placing API Gateway in front of the service.

## Decision

Use CloudFront as the public edge distribution with AWS WAF attached, forwarding to an ALB origin.

## Rationale

CloudFront provides an edge entry point for all API traffic and can cache `/api/market/*` responses for one hour. That reduces repeated load on ECS and PostgreSQL for market snapshots.

AWS WAF attaches at CloudFront with managed rule groups and webhook rate limiting. This keeps common request filtering at the edge before traffic reaches the ALB.

The ALB remains useful as the regional origin because it integrates directly with ECS target groups, health checks, optional HTTPS listeners, and path-based routing. The default validation mode uses the generated CloudFront domain and sends origin traffic to the ALB over HTTP from the CloudFront origin-facing prefix list. Custom-domain mode can add ACM/Route53 and HTTPS at the ALB origin later.

API Gateway is a strong option for API management, but this project already uses ALB-native ECS service routing and CloudFront caching. Adding API Gateway would increase the number of routing layers without a current requirement for API Gateway-specific features.

## Consequences

- The ALB security group accepts origin traffic only from the CloudFront origin-facing managed prefix list.
- CloudFront cache behavior must avoid caching dynamic webhook and lead query responses.
- Market snapshot responses must emit cache headers compatible with the CloudFront cache policy.
- WAF rules and CloudFront distribution settings are part of the validation evidence.
