# Test Results

Last verified: 2026-05-12 18:40 EDT from `/Users/aiden/clearpath-fargate-api-work`.

## Local Validation

Command:

```bash
make validate
```

Result: passed.

Summary:

| Check | Result |
|---|---|
| FastAPI test suite | `13 passed` |
| Terraform format check | Passed |
| Terraform init with backend disabled | Passed |
| Terraform validate | Passed |
| Kubernetes manifest render | Passed: local overlay rendered 8 objects, EKS overlay rendered 9 objects |
| Checkov Terraform scan | `339 passed`, `0 failed`, `44 skipped` |
| Checkov Kubernetes scan | `96 passed`, `0 failed`, `1 skipped` |
| Alembic sanity check | Initial revision discovered with `alembic history`; migration files compile |

## GitHub Actions

Latest `Build and Deploy` push workflow for commit `4c1c942` passed on 2026-05-12:

- Python dependencies installed
- FastAPI tests passed
- Hadolint passed
- Docker image built successfully
- ECR push / ECS deployment job skipped because it only runs on manual dispatch with `deploy=true`

The `Terraform Validate` workflow includes Kubernetes render validation with `kubectl` installed and remains scoped to infrastructure or Kubernetes changes.

## Deployed CloudFront Smoke Artifact

During the short-lived AWS validation run on 2026-05-10, the API responded through the generated CloudFront URL:

```bash
curl -f https://<generated-cloudfront-domain>/health
```

Response:

```json
{"status":"ok","service":"clearpath-api"}
```

Evidence:

![CloudFront health response](screenshots/live-validation/01-cloudfront-health-response.png)

The AWS stack was destroyed after evidence capture to avoid ongoing cost. A future paid validation window should capture the full deployed smoke set: `/ready`, `/webhooks/ghl`, protected `/api/leads`, `/api/market/gwinnett`, and CloudFront cache headers.
