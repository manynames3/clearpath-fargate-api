# Live Validation Summary

## Status

A short-lived AWS validation run was completed on 2026-05-10 and the Terraform-managed stack was destroyed afterward to avoid ongoing cloud cost.

The validation proved the AWS deployment path for the API:

- reviewed Terraform plan before apply
- ECS Fargate service running the container
- two healthy Fargate tasks
- ALB target groups for API and webhook paths
- RDS PostgreSQL in private networking
- RDS Proxy available and attached to the database
- CloudFront distribution serving `/health`
- WAF attached to CloudFront
- CloudWatch metrics and alarms visible
- VPC with public, private ECS, and private database tiers

## Evidence Handling

Public-safe screenshot crops from the validation run are committed under [screenshots/live-validation](screenshots/live-validation/README.md). Raw screenshots from the validation run are kept locally under the ignored `docs/evidence/` path because they contain AWS account metadata, ARNs, generated endpoints, private network identifiers, and secret ARNs. Do not commit raw AWS console screenshots without redaction.

For public documentation, redact:

- AWS account ID
- AWS account alias/user menu text
- full ARNs
- Secrets Manager ARNs and generated secret names
- private IP addresses when not needed to explain the architecture

Keep visible:

- resource names
- status and health indicators
- service relationships
- target health
- WAF attachment
- CloudWatch graphs and alarm states

## Validation Notes

The live validation surfaced normal first-run issues that were resolved during the paid window:

- new AWS Free Tier plan restrictions blocked RDS Proxy until the account was upgraded to a paid plan
- initial ECS tasks failed health checks during early revisions, then stabilized after the image/startup path was corrected and the service reached two healthy tasks
- KMS console visibility warnings were reviewed without publishing key policy details or full key ARNs

These notes are included because they show the deployment was exercised like a real infrastructure rollout, not only planned locally.

## Teardown Result

Terraform destroy completed with `0 added, 0 changed, 93 destroyed`.

Post-destroy verification showed the active stack removed:

- Terraform state list empty
- ECS cluster inactive and no active task definitions
- RDS instance not found
- RDS Proxy not found
- ALB not found
- CloudFront distribution not found
- VPC resources not found
- Secrets Manager project secrets not listed

KMS keys may remain in `PendingDeletion` during the AWS-managed deletion window. Resource Groups Tagging API may temporarily list deleted or inactive resources due to eventual consistency.

## GoHighLevel Status

The deployed API proved the GHL-style receiver path, not a live external GoHighLevel workflow.

Remaining work to prove live GHL integration:

1. Get access to the target GHL account/location.
2. Create or edit the motivated-seller workflow.
3. Add a Custom Webhook action that posts to the deployed `api_base_url`.
4. Add the shared webhook secret header.
5. Send a real workflow event.
6. Capture the GHL delivery log.
7. Query `/api/leads` with the API key and capture the created lead.

Until that is completed, describe the feature as a GoHighLevel-compatible webhook receiver rather than a fully verified live GHL integration.
