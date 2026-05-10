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
2. Set `route53_zone_id` in `terraform/environments/dev/terraform.tfvars` if DNS/ACM should be created.
3. Review `api_domain_name` and `origin_domain_name`.
4. Set `TF_VAR_origin_header_value` to a one-time high-entropy value for CloudFront-to-ALB origin protection.
5. Run `terraform plan -out=tfplan` from `terraform/environments/dev`.
6. Review the full plan output before applying.

`make preflight` is non-deploying. It checks tools, AWS identity, Terraform settings, local tests, Terraform validation, and Checkov. It does not run `terraform plan`, `terraform apply`, Docker image builds, image pushes, or AWS create/update/delete commands.

Example origin header setup for the deploy shell:

```bash
export TF_VAR_origin_header_value="$(openssl rand -hex 32)"
```

This value is used by CloudFront and ALB listener rules to reduce direct-origin access. Do not commit the value.

## After Apply

Load runtime secret values without putting them in Terraform:

```bash
aws secretsmanager put-secret-value \
  --secret-id clearpath/dev/ghl-webhook \
  --secret-string "$GHL_WEBHOOK_SECRET"

aws secretsmanager put-secret-value \
  --secret-id clearpath/dev/api-key \
  --secret-string "$CLEARPATH_API_KEY"
```

Configure the GoHighLevel Workflow Custom Webhook to send `POST` requests to:

```text
https://api.clearpathpropertygroup.com/webhooks/ghl
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

## Health Checks

```bash
curl -f https://api.clearpathpropertygroup.com/health
curl -f https://api.clearpathpropertygroup.com/ready
curl -I https://api.clearpathpropertygroup.com/api/market/gwinnett
curl -f "https://api.clearpathpropertygroup.com/api/leads?county=Gwinnett&status=warm" \
  -H "X-Clearpath-API-Key: <redacted>"
```

The second market request should return a CloudFront cache hit after the first successful origin response.
