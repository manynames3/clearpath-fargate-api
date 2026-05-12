# Runbook

## Local Checks

```bash
.venv/bin/pytest app/tests
terraform -chdir=terraform/environments/dev init -backend=false
terraform -chdir=terraform/environments/dev validate
.venv/bin/checkov -d terraform/ --framework terraform --quiet
```

## Before Apply

1. Run `make preflight` from the repository root.
2. Confirm the AWS account is not on a restricted Free Tier plan that blocks paid services. RDS Proxy may fail with `FreeTierRestrictionError` until the account is upgraded to the paid plan.
3. Keep `use_custom_domain = false` for the default no-domain validation path.
4. Only set `use_custom_domain = true`, `route53_zone_id`, `api_domain_name`, and `origin_domain_name` if you own a domain and intentionally want Route53/ACM resources.
5. Set `TF_VAR_origin_header_value` to a one-time high-entropy value for CloudFront-to-ALB origin protection.
6. Run `terraform plan -out=tfplan` from `terraform/environments/dev`.
7. Review the full plan output before applying.

`make preflight` is non-deploying. It checks tools, AWS identity, Terraform settings, local tests, Terraform validation, and Checkov. It does not run `terraform plan`, `terraform apply`, Docker image builds, image pushes, or AWS create/update/delete commands.

Example origin header setup for the deploy shell:

```bash
export TF_VAR_origin_header_value="$(openssl rand -hex 32)"
```

This value is used by CloudFront and ALB listener rules to reduce direct-origin access. Do not commit the value.

## After Apply

Read the deployed base URL from Terraform. In the default no-domain mode this is the generated CloudFront domain:

```bash
export API_BASE_URL="$(terraform -chdir=terraform/environments/dev output -raw api_base_url)"
```

Load runtime secret values without putting them in Terraform:

```bash
aws secretsmanager put-secret-value \
  --secret-id clearpath/dev/ghl-webhook \
  --secret-string "$GHL_WEBHOOK_SECRET"

aws secretsmanager put-secret-value \
  --secret-id clearpath/dev/api-key \
  --secret-string "$CLEARPATH_API_KEY"
```

If validating the external GHL path, add a GoHighLevel Workflow Custom Webhook action to the existing paid-lead intake workflow. Leave existing GHL notifications, follow-up sequences, pipeline actions, and Notion handoff in place; the Clearpath webhook is the reporting/source-accountability copy.

Configure the Custom Webhook to send `POST` requests to:

```text
$API_BASE_URL/webhooks/ghl
```

Use [ghl-integration.md](ghl-integration.md) for the expected payload fields and shared secret header.

Run the schema migration from an environment that can reach the private RDS Proxy endpoint:

```bash
export AWS_REGION=us-east-1
export PROXY_ENDPOINT="$(terraform -chdir=terraform/environments/dev output -raw rds_proxy_endpoint)"
scripts/migrate.sh
```

Build and push the image through the manual GitHub Actions workflow described in [github-deploy-setup.md](github-deploy-setup.md). This is the preferred path because local Docker is not required. Use it only after the infrastructure is already applied and the GHL secret value is loaded.

The deploy workflow is manual-gated. It only pushes an image and forces a new ECS deployment when run with `deploy=true`.

## Free Tier Restriction Recovery

If Terraform fails while creating RDS Proxy with an AWS Free Tier restriction, do not remove RDS Proxy from the architecture just to get past the apply. Upgrade the AWS account plan, rerun validation and Checkov, generate a fresh Terraform plan, review it, and apply that saved continuation plan.

After the paid-plan upgrade, expect the continuation plan to create the RDS Proxy, RDS Proxy target, ECS task definition, ECS service, and any remaining observability resources. Then continue with the GitHub Actions image build/push flow.

## Health Checks

```bash
curl -f "$API_BASE_URL/health"
curl -f "$API_BASE_URL/ready"
curl -I "$API_BASE_URL/api/market/gwinnett"
curl -f "$API_BASE_URL/api/leads?county=Gwinnett&status=warm" \
  -H "X-Clearpath-API-Key: <redacted>"
curl -f "$API_BASE_URL/api/intelligence/summary" \
  -H "X-Clearpath-API-Key: <redacted>"
curl -f "$API_BASE_URL/api/intelligence/lead-scores?needs_review=true" \
  -H "X-Clearpath-API-Key: <redacted>"
```

The second market request should return a CloudFront cache hit after the first successful origin response.
Open `$API_BASE_URL/dashboard` to verify the internal lead intelligence dashboard loads through CloudFront.
