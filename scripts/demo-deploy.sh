#!/usr/bin/env bash
#
# Deploy a specific commit's images from GHCR into the current Kubernetes
# cluster. This is the last step of the M10 live demo: after the pipeline has
# pushed images tagged with a commit SHA, this rolls the deployment onto them.
#
# Usage:
#   ./scripts/demo-deploy.sh            # uses the current commit's short SHA
#   ./scripts/demo-deploy.sh 7922c0a    # or an explicit SHA
#
# Requires: helm, kubectl pointed at the target cluster, and the images to be
# published (the CI/CD run for that commit must have finished).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

NAMESPACE="clinicdesk"
RELEASE="clinicdesk"
# Images are published under ghcr.io/<owner>/<repo>, lowercase — matching the
# workflow, which lowercases $GITHUB_REPOSITORY ("owner/repo"). Derive it from
# the git remote rather than hardcoding the owner's casing.
SLUG="$(git -C "$ROOT" remote get-url origin \
  | sed -E 's#.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##' | tr '[:upper:]' '[:lower:]')"
REGISTRY="ghcr.io"

SHA="${1:-$(git -C "$ROOT" rev-parse --short HEAD)}"

if ! git -C "$ROOT" cat-file -e "${SHA}^{commit}" 2>/dev/null; then
  echo "error: '$SHA' is not a commit in this repository" >&2
  exit 1
fi

echo "==> Deploying commit $SHA from ${REGISTRY}/${SLUG}"
echo "    (the CI/CD run for this commit must have finished and pushed the images)"

helm upgrade --install "$RELEASE" "$ROOT/helm/clinicdesk" \
  --namespace "$NAMESPACE" --create-namespace \
  --set images.backend.repository="${REGISTRY}/${SLUG}/backend" \
  --set images.backend.tag="$SHA" \
  --set images.frontend.repository="${REGISTRY}/${SLUG}/frontend" \
  --set images.frontend.tag="$SHA" \
  --set backend.podAnnotations."clinicdesk\.local/deployed-sha"="$SHA" \
  --set frontend.podAnnotations."clinicdesk\.local/deployed-sha"="$SHA" \
  --wait --timeout 240s

echo
echo "==> Rollout status"
kubectl -n "$NAMESPACE" rollout status deploy/clinicdesk-backend --timeout=120s
kubectl -n "$NAMESPACE" rollout status deploy/clinicdesk-frontend --timeout=120s

echo
echo "==> Running images"
kubectl -n "$NAMESPACE" get pods \
  -o custom-columns='POD:.metadata.name,IMAGE:.spec.containers[*].image,STATUS:.status.phase'

echo
echo "==> Open the app at http://localhost:18080"
echo "    kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 18080:80"
echo "    The badge next to the page title must read: $SHA"
