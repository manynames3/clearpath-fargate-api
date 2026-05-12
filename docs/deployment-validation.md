# Deployment Validation

This project should be deployed only long enough to capture evidence, then destroyed. RDS PostgreSQL is implemented for the current workload because it is cheaper and simpler than Aurora, while Aurora remains a documented upgrade path.

## Short-Lived AWS Validation

Run this only during an intentional validation window. Always review the plan before apply.
Read [cost-estimate.md](cost-estimate.md) before applying in AWS.

## AWS Account Plan Requirement

Use an AWS account that allows paid resources before running the full validation apply. Some new AWS Free Tier plan accounts block resources that this stack intentionally uses, including RDS Proxy. In that case Terraform may fail with an AWS `FreeTierRestrictionError` when creating the proxy.

For this project, RDS Proxy is not optional in the production-pattern architecture: ECS Fargate tasks connect through the proxy so database connections are pooled before reaching PostgreSQL. If the account is still on a restricted Free Tier plan, upgrade the account plan first, then rerun `terraform plan` and apply the reviewed continuation plan.

The $100 Free Tier credit can still reduce eligible usage after upgrading, but it is not a hard spending cap. Keep the validation window short, capture evidence immediately, and destroy the stack the same day.

From the repository root, run the non-deploying preflight first:

```bash
make preflight
```

## Paid Window Evidence Checklist

Keep the live window focused on evidence, not extra build work:

- Run and save the reviewed Terraform plan.
- Apply once, then capture the Terraform summary and key outputs.
- Record `terraform output -raw api_base_url`. The default validation path uses the generated CloudFront domain and does not require a purchased domain.
- Confirm CloudFront sends the origin header and ALB listener rules require it.
- Trigger GitHub Actions `Build and Deploy` manually with `deploy=true`.
- Capture ECS service health, task health, ALB target health, RDS Proxy target health, CloudFront deployed status, and WAF attachment.
- Run API smoke tests through `api_base_url`, including `/health`, `/ready`, a GHL-style test payload to `/webhooks/ghl`, protected `/api/leads`, `/api/intelligence/summary`, `/api/intelligence/source-performance`, `/api/intelligence/lead-scores?needs_review=true`, and `/api/market/gwinnett`.
- Open `/dashboard` through `api_base_url` and capture the internal source scorecard, duplicate alerts, lead scores, and county performance view.
- If a real GoHighLevel account is available, add the Clearpath Custom Webhook action to the existing paid-lead intake workflow and capture the workflow delivery log. Otherwise, document the endpoint as GHL-ready but not externally connected.
- Capture CloudFront cache headers on the second market endpoint request.
- Run `make deployment-evidence` to save read-only AWS CLI output.
- Destroy the stack the same day and capture the destroy summary.

```bash
cd terraform/environments/dev
terraform plan -out=tfplan
terraform apply tfplan
```

After apply, configure the manual GitHub Actions image deployment path from [github-deploy-setup.md](github-deploy-setup.md), then run the `Build and Deploy` workflow with `deploy=true`. This builds the image in GitHub Actions, pushes it to ECR, and forces a new ECS deployment. Local Docker is not required for the preferred validation path.

After apply, capture:

- Terraform apply summary
- VPC with `10.0.0.0/16`, six subnets across two AZs, and VPC Flow Logs
- Route tables showing public IGW routing, private app NAT routing, and isolated database routing
- Security groups showing CloudFront to ALB to ECS to RDS Proxy to RDS
- ECS cluster and service with healthy task count
- ECS task definition showing environment variables sourced from ARNs, not plaintext secrets
- ALB target group health checks passing
- RDS PostgreSQL instance private/public accessibility settings
- RDS Proxy target health
- CloudFront distribution deployed
- WAF WebACL attached to CloudFront
- CloudWatch dashboard and alarms
- API health response through `api_base_url`
- API readiness response proving database connectivity through `api_base_url`
- GHL-style webhook receiver test returning `{"status":"accepted"}` and creating a lead
- optional real GoHighLevel workflow delivery log from the paid-lead intake workflow, if a GHL account/location was connected during the validation window
- protected `/api/leads` response using `X-Clearpath-API-Key`
- protected `/api/intelligence/summary` response showing lead/source/duplicate/review totals
- protected `/api/intelligence/source-performance` response showing source/vendor scorecard data
- protected `/api/intelligence/lead-scores?needs_review=true` response showing score reasons
- `/dashboard` screenshot showing the end-user product surface
- `/api/market/gwinnett` response with cache headers

Use [deployment-evidence-template.md](deployment-evidence-template.md) as the screenshot and command-output checklist. Store screenshots in `docs/screenshots/`.

## GoHighLevel Validation Plan

Do this only if the GHL account/location is available during the paid AWS window. The purpose is to prove the API receives a copy of the real lead-intake event for reporting; it is not meant to replace GHL's CRM automation.

1. Use the existing paid lead provider intake workflow when possible. If that workflow cannot be safely edited, clone it or create a temporary validation workflow triggered by a test contact/tag.
2. Leave existing GHL actions in place: notifications, follow-up sequences, pipeline movement, and Notion handoff.
3. Add a Custom Webhook action that posts to `$API_BASE_URL/webhooks/ghl`.
4. Include `X-Clearpath-Webhook-Secret` with the secret value loaded into Secrets Manager; do not expose the value in screenshots.
5. Send mapped contact, source/vendor, and property fields.
6. Trigger one paid-lead-style validation contact.
7. Capture the GHL workflow execution/delivery log showing a `200` response from Clearpath API.
8. Query `/api/leads` with `X-Clearpath-API-Key` and capture the stored lead/source/property data.
9. Query `/api/intelligence/source-performance` and `/api/intelligence/lead-scores?needs_review=true` to show the lead now participates in the reporting layer.
10. Open `/dashboard` and capture the same source/vendor and review queue evidence.
11. Disable or remove the temporary webhook action before teardown if it points to the generated CloudFront URL.

Collect read-only AWS CLI output into `docs/evidence/<timestamp>/`:

```bash
make deployment-evidence
```

Then destroy the stack the same day.

```bash
cd ../../..
scripts/teardown.sh
```

If using manual commands instead of the teardown script, follow [teardown.md](teardown.md).

## Production Hardening Notes

The default dev settings prioritize cost and clean teardown. For a real production deployment:

- use `terraform/environments/dev/production.tfvars.example` as the starting override file
- enable RDS Multi-AZ
- set retained RDS backups with `rds_backup_retention_days = 7` or higher
- increase the RDS instance class after load testing
- set `rds_deletion_protection = true`
- set `rds_skip_final_snapshot = false` and provide `rds_final_snapshot_identifier`
- set `alb_deletion_protection = true`
- preserve SSL enforcement with `rds.force_ssl = 1`
- keep RDS Proxy between ECS and PostgreSQL
- tune ECS desired count and autoscaling from observed request volume
- keep CloudFront caching on market snapshots

Aurora PostgreSQL is the future upgrade path when workload patterns justify it: high concurrency, read replica needs, stricter failover goals, or more dynamic capacity scaling.

## Kubernetes Validation

The repo includes a source-only Kubernetes track under `k8s/`. For local Kubernetes validation, run the local overlay in kind or minikube and capture:

- `kubectl get deploy,svc,hpa,pdb -n clearpath-api`
- rollout status for `deployment/clearpath-api`
- readiness/liveness probe configuration
- `curl http://localhost:8000/health` through port-forward

Do not create an EKS cluster unless you intentionally want a separate paid validation window.
