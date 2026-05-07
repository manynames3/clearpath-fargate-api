#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform/environments/dev"

cd "$TF_DIR"

if terraform output -raw ecs_cluster_name >/tmp/clearpath-ecs-cluster 2>/dev/null \
  && terraform output -raw ecs_service_name >/tmp/clearpath-ecs-service 2>/dev/null; then
  ECS_CLUSTER="$(cat /tmp/clearpath-ecs-cluster)"
  ECS_SERVICE="$(cat /tmp/clearpath-ecs-service)"

  echo "Scaling ECS service to zero before destroy: $ECS_CLUSTER/$ECS_SERVICE"
  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --desired-count 0 >/dev/null

  aws ecs wait services-stable \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE"
else
  echo "No ECS outputs found; continuing to Terraform destroy plan."
fi

terraform plan -destroy -out=destroy.tfplan

echo
echo "Review the destroy plan above."
read -r -p "Apply this destroy plan now? Type 'yes' to continue: " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
  echo "Destroy cancelled. Plan remains at $TF_DIR/destroy.tfplan."
  exit 0
fi

terraform apply destroy.tfplan
