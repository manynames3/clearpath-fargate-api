# GitHub Deploy Setup

The application image is deployed through the manual `.github/workflows/build-push.yml` workflow. Local Docker is optional; the preferred validation path is to let GitHub Actions build the image, push it to ECR, and force a new ECS deployment after Terraform has created the AWS resources.

The workflow is intentionally gated. A normal push runs tests and Hadolint for app changes, but it does not push an image or update ECS. Image deployment only happens when the workflow is started manually with `deploy=true`.

## When To Configure This

Configure these settings after `terraform apply` has created:

- ECR repository
- ECS cluster
- ECS service
- IAM task and execution roles

The workflow expects those resources to already exist.

## GitHub Repository Variables

Set these repository variables in GitHub Actions:

| Variable | Value |
|---|---|
| `AWS_REGION` | AWS region used by Terraform, for example `us-east-1` |
| `ECR_REPOSITORY` | ECR repository name, for example `clearpath/api` |
| `ECS_CLUSTER` | Terraform output `ecs_cluster_name` |
| `ECS_SERVICE` | Terraform output `ecs_service_name` |

Useful commands after apply:

```bash
terraform -chdir=terraform/environments/dev output -raw ecs_cluster_name
terraform -chdir=terraform/environments/dev output -raw ecs_service_name
terraform -chdir=terraform/environments/dev output -raw ecr_repository_url
```

For `ecr_repository_url` shaped like:

```text
<aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com/clearpath/api
```

use:

- `ECR_REGISTRY=<aws-account-id>.dkr.ecr.<aws-region>.amazonaws.com`
- `ECR_REPOSITORY=clearpath/api`

## GitHub Repository Secrets

Set these repository secrets:

| Secret | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the AWS IAM role assumed by GitHub Actions through OIDC |
| `ECR_REGISTRY` | ECR registry host, without the repository path |

`ECR_REGISTRY` is a secret instead of a variable so account-specific registry details are not shown in workflow logs by default.

## OIDC Trust Policy

The deploy role should trust GitHub Actions through the GitHub OIDC provider. Replace placeholders before creating the role.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<aws-account-id>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:manynames3/clearpath-fargate-api:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

If the GitHub OIDC provider does not exist in the AWS account, create it before creating the deploy role.

## Required Deploy Role Permissions

The workflow needs to authenticate to ECR, push image layers, push image tags, and force a new deployment on the existing ECS service. Replace placeholders with the actual region, account ID, repository name, cluster name, and service name.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AuthenticateToECR",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "PushToRepository",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Resource": "arn:aws:ecr:<aws-region>:<aws-account-id>:repository/<ecr-repository-name>"
    },
    {
      "Sid": "UpdateExistingECSService",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:UpdateService"
      ],
      "Resource": "arn:aws:ecs:<aws-region>:<aws-account-id>:service/<ecs-cluster-name>/<ecs-service-name>"
    }
  ]
}
```

`ecr:GetAuthorizationToken` requires `Resource: "*"`. The ECR push and ECS update permissions should stay scoped to the exact repository and service.

## Manual Deployment Flow

After Terraform apply and GitHub repository settings are in place:

1. Open GitHub Actions.
2. Select `Build and Deploy`.
3. Choose `Run workflow`.
4. Set `deploy=true`.
5. Start the workflow from `main`.
6. Wait for the `build-push` job to complete.
7. Confirm ECS starts a new deployment and tasks become healthy.

CLI equivalent:

```bash
gh workflow run build-push.yml --repo manynames3/clearpath-fargate-api --ref main -f deploy=true
```

Then verify ECS:

```bash
aws ecs describe-services \
  --cluster "$(terraform -chdir=terraform/environments/dev output -raw ecs_cluster_name)" \
  --services "$(terraform -chdir=terraform/environments/dev output -raw ecs_service_name)" \
  --query 'services[0].{Running:runningCount,Desired:desiredCount,Status:status}'
```

## What This Workflow Does Not Do

The GitHub workflow does not:

- create AWS infrastructure
- run Terraform
- create or rotate secrets
- apply database schema migrations
- seed data
- run teardown

Run infrastructure, secrets, schema setup, validation evidence, and teardown through the deployment runbook.
