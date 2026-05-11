# Validation Troubleshooting Notes

During the short-lived AWS validation run, the stack was deployed, observed, fixed, and destroyed the same day. The final state was healthy, but two first-run issues were useful to document because they reflect real cloud rollout behavior.

## AWS Account Plan Restriction

RDS Proxy creation failed while the AWS account was still on a restricted Free Tier plan. The project intentionally keeps RDS Proxy in the architecture because Fargate tasks should not connect directly to PostgreSQL under production-style traffic. The account was upgraded to a paid plan, the reviewed Terraform apply was rerun, and RDS Proxy was created successfully.

## ECS Health Check Stabilization

Initial ECS task revisions reached `RUNNING` but reported unhealthy container or target group status while the deployment was still rolling forward. The final deployed task revision stabilized with two healthy Fargate tasks and healthy ALB API and webhook target groups.

Public-safe troubleshooting crops are stored under [screenshots/troubleshooting](screenshots/troubleshooting/). They are intentionally not used as the primary README evidence because the final portfolio story should lead with the healthy deployed state.
