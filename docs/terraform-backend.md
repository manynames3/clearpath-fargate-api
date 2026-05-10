# Terraform Remote State

Local state is acceptable for the source-only portfolio build and local validation. For a real AWS validation window shared across machines, use encrypted S3 remote state with state locking before applying.

## Setup

1. Create a private S3 bucket for Terraform state in the AWS account.
2. Enable bucket versioning and default encryption.
3. Block all public access on the bucket.
4. Copy `terraform/environments/dev/backend.tf.example` to `terraform/environments/dev/backend.tf`.
5. Replace placeholders with the real bucket name and region.
6. Run:

```bash
terraform -chdir=terraform/environments/dev init -migrate-state
```

The example uses Terraform's S3 lockfile support through `use_lockfile = true`. If your Terraform/AWS provider setup requires DynamoDB locking instead, keep the same backend shape but add a dedicated lock table outside this repo and document the table name in your private deployment notes.

Do not commit the real `backend.tf` if it contains account-specific bucket names or environment details.
