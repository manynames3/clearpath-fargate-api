#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform/environments/dev"
TFVARS="$TF_DIR/terraform.tfvars"
CHECKOV_BIN="${CHECKOV:-$ROOT_DIR/.venv/bin/checkov}"

failures=0

section() {
  printf '\n== %s ==\n' "$1"
}

pass() {
  printf '[ok] %s\n' "$1"
}

warn() {
  printf '[warn] %s\n' "$1"
}

fail() {
  printf '[fail] %s\n' "$1"
  failures=$((failures + 1))
}

require_command() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "$1 found: $(command -v "$1")"
  else
    fail "$1 is required but was not found"
  fi
}

section "Scope"
cat <<'EOF'
This preflight is non-deploying. It does not run terraform plan, terraform apply,
docker build, docker push, GitHub workflows, or any AWS create/update/delete command.
EOF

section "Required tools"
require_command terraform
require_command aws
require_command curl

if command -v docker >/dev/null 2>&1; then
  pass "docker found: $(command -v docker)"
else
  warn "docker not found; image build/push will not work during deployment validation"
fi

if [[ -x "$CHECKOV_BIN" ]]; then
  pass "checkov found: $CHECKOV_BIN"
else
  fail "checkov not found at $CHECKOV_BIN; run make install or set CHECKOV=/path/to/checkov"
fi

section "AWS identity"
if aws sts get-caller-identity >/tmp/clearpath-preflight-identity.json 2>/tmp/clearpath-preflight-identity.err; then
  ACCOUNT_ID="$(python3 - <<'PY'
import json
with open("/tmp/clearpath-preflight-identity.json", encoding="utf-8") as f:
    print(json.load(f).get("Account", "unknown"))
PY
)"
  ARN="$(python3 - <<'PY'
import json
with open("/tmp/clearpath-preflight-identity.json", encoding="utf-8") as f:
    print(json.load(f).get("Arn", "unknown"))
PY
)"
  pass "AWS identity available: account=$ACCOUNT_ID arn=$ARN"
else
  warn "AWS identity unavailable; configure credentials before an AWS validation run"
fi
rm -f /tmp/clearpath-preflight-identity.json /tmp/clearpath-preflight-identity.err

section "Terraform tfvars"
if [[ -f "$TFVARS" ]]; then
  pass "terraform.tfvars found"
else
  fail "terraform.tfvars not found at $TFVARS"
fi

if grep -Eq 'route53_zone_id[[:space:]]*=[[:space:]]*""' "$TFVARS"; then
  warn "route53_zone_id is empty; DNS/ACM records remain disabled for local-only validation"
else
  pass "route53_zone_id appears to be set"
fi

if grep -Eq 'rds_multi_az[[:space:]]*=[[:space:]]*false' "$TFVARS"; then
  pass "rds_multi_az=false for cost-controlled dev validation"
else
  warn "rds_multi_az is not false; review expected cost and availability posture"
fi

if grep -Eq 'rds_deletion_protection[[:space:]]*=[[:space:]]*false' "$TFVARS"; then
  pass "rds_deletion_protection=false for clean teardown"
else
  warn "rds_deletion_protection is not false; destroy may require manual changes"
fi

if grep -Eq 'alb_deletion_protection[[:space:]]*=[[:space:]]*false' "$TFVARS"; then
  pass "alb_deletion_protection=false for clean teardown"
else
  warn "alb_deletion_protection is not false; destroy may require manual changes"
fi

section "Local validation"
(
  cd "$ROOT_DIR"
  make validate
)

section "Result"
if [[ "$failures" -gt 0 ]]; then
  fail "$failures blocking preflight check(s) failed"
  exit 1
fi

pass "preflight completed without blocking failures"
