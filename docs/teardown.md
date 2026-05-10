# Teardown

This stack is designed to be destroyed after validation runs.

## Drain ECS

```bash
aws ecs update-service \
  --cluster clearpath-api-dev \
  --service clearpath-api \
  --desired-count 0

aws ecs wait services-stable \
  --cluster clearpath-api-dev \
  --services clearpath-api
```

## Destroy

CloudFront distributions take time to disable and delete. If a full destroy is blocked by CloudFront or ACM dependencies, destroy in stages:

```bash
# From the repository root:
scripts/teardown.sh
```

The script scales ECS to zero, prints a Terraform destroy plan, and asks for confirmation before applying it.

For manual teardown:

```bash
cd terraform/environments/dev
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

If staged teardown is needed:

```bash
terraform destroy -target=module.dns_records
terraform destroy -target=module.cloudfront
terraform destroy
```

## Verify

```bash
aws ecs list-clusters
aws rds describe-db-instances --query 'DBInstances[?starts_with(DBInstanceIdentifier, `clearpath-api`)]'
aws cloudfront list-distributions --query 'DistributionList.Items[?Comment==`clearpath-api`]'
```

The expected result after teardown is no Clearpath ECS clusters, RDS database instances, or CloudFront distributions.

## Post-Destroy Notes

After `terraform apply destroy.tfplan` completes, run service-specific verification instead of relying only on the Resource Groups Tagging API. The tagging API can temporarily show deleted, inactive, or pending-deletion resources after a destroy.

Expected post-destroy states:

- Terraform state list is empty.
- ECS cluster is `INACTIVE`; active task definition count is `0`.
- RDS database instance is not found.
- RDS Proxy is not found.
- ALB is not found.
- CloudFront distribution is not found.
- VPC, security groups, and VPC endpoints with `Project=clearpath-api` are not found.
- Customer-managed KMS keys are `PendingDeletion` because AWS enforces a deletion window.
- Secrets Manager project secrets are not listed.

Inactive ECS task definition revisions and KMS keys pending deletion are normal AWS teardown artifacts. They do not mean the application stack is still running.
