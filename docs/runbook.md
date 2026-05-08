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
4. Run `terraform plan -out=tfplan` from `terraform/environments/dev`.
5. Review the full plan output before applying.

`make preflight` is non-deploying. It checks tools, AWS identity, Terraform settings, local tests, Terraform validation, and Checkov. It does not run `terraform plan`, `terraform apply`, Docker image builds, image pushes, or AWS create/update/delete commands.

## After Apply

Load the GHL webhook HMAC secret without putting it in Terraform:

```bash
aws secretsmanager put-secret-value \
  --secret-id clearpath/dev/ghl-webhook \
  --secret-string "$GHL_WEBHOOK_SECRET"
```

Configure the GoHighLevel Workflow Custom Webhook to send `POST` requests to:

```text
https://api.clearpathpropertygroup.com/webhooks/ghl
```

Use [ghl-integration.md](ghl-integration.md) for the expected payload fields and shared secret header.

Run the schema migration through RDS Proxy:

```bash
export AWS_REGION=us-east-1
export PROXY_ENDPOINT="$(terraform -chdir=terraform/environments/dev output -raw rds_proxy_endpoint)"
scripts/migrate.sh
```

Build and push the image only when ready to deploy:

```bash
docker build -t clearpath-api app/
```

The GitHub deploy workflow is manual-gated. Use it only after the infrastructure is already applied and the GHL secret value is loaded.

## Health Checks

```bash
curl -f https://api.clearpathpropertygroup.com/health
curl -I https://api.clearpathpropertygroup.com/api/market/gwinnett
```

The second market request should return a CloudFront cache hit after the first successful origin response.
