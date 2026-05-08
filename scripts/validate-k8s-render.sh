#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if command -v kubectl >/dev/null 2>&1; then
  RENDER_CMD=(kubectl kustomize)
elif command -v kustomize >/dev/null 2>&1; then
  RENDER_CMD=(kustomize build)
else
  echo "[warn] kubectl or kustomize not found; skipping Kubernetes render validation"
  echo "[warn] Install kubectl or kustomize to validate k8s/overlays/local and k8s/overlays/eks"
  exit 0
fi

for overlay in k8s/overlays/local k8s/overlays/eks; do
  output="$TMP_DIR/$(basename "$overlay").yaml"
  echo "Rendering $overlay"
  "${RENDER_CMD[@]}" "$ROOT_DIR/$overlay" >"$output"

  if [[ ! -s "$output" ]]; then
    echo "[fail] $overlay rendered empty output" >&2
    exit 1
  fi

  objects="$(grep -c '^kind:' "$output" || true)"
  if [[ "$objects" -eq 0 ]]; then
    echo "[fail] $overlay rendered no Kubernetes objects" >&2
    exit 1
  fi

  echo "[ok] $overlay rendered $objects Kubernetes object(s)"
done
