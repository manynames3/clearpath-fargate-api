# Teardown

This stack is designed to be destroyed after demos.

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
