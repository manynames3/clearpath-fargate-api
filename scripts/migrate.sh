#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION before running migrations.}"
: "${PROXY_ENDPOINT:?Set PROXY_ENDPOINT to the RDS Proxy endpoint hostname.}"
: "${DB_USER:=clearpath_admin}"
: "${DB_NAME:=clearpath}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PGPASSWORD="$(
  aws rds generate-db-auth-token \
    --hostname "$PROXY_ENDPOINT" \
    --port 5432 \
    --region "$AWS_REGION" \
    --username "$DB_USER"
)"

psql "host=$PROXY_ENDPOINT port=5432 user=$DB_USER dbname=$DB_NAME sslmode=require" \
  -v ON_ERROR_STOP=1 \
  -f "$ROOT_DIR/sql/schema.sql"
