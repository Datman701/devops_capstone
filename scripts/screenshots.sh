#!/usr/bin/env bash
#
# Regenerates the submission screenshots in docs/screenshots/.
#
#   ./scripts/screenshots.sh            # everything that can run locally
#   ./scripts/screenshots.sh app        # application pages only (M1)
#   ./scripts/screenshots.sh k8s        # through the Kubernetes Ingress (M8)
#   ./scripts/screenshots.sh monitoring # Grafana dashboard (M9)
#   ./scripts/screenshots.sh terminal   # pytest / docker / trivy / terraform
#
# GitHub-hosted captures (the Actions run and GHCR package pages) are fetched
# with a small inline CDP helper rather than a script, because they need the run
# id of a completed, successful pipeline run.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/docs/screenshots"
WORK="${SCREENSHOT_WORK_DIR:-/tmp/opencode/evidence}"
COMPOSE_URL="${COMPOSE_URL:-http://127.0.0.1:3000}"
INGRESS_URL="${INGRESS_URL:-http://127.0.0.1:18080}"
GRAFANA_URL="${GRAFANA_URL:-http://127.0.0.1:13000}"
PROM_URL="${PROM_URL:-http://127.0.0.1:19090}"

mkdir -p "$OUT" "$WORK"
cd "$ROOT"

term() {
  node scripts/render-terminal.mjs "$@"
}

# ---------- Application (M1) ----------
capture_app() {
  echo "==> application pages ($COMPOSE_URL)"
  node scripts/screenshots.mjs "$COMPOSE_URL" "$OUT"
}

# ---------- Terminal evidence (M2-M7) ----------
capture_terminal() {
  echo "==> pytest"
  (
    cd backend
    DATABASE_URL="postgresql+psycopg://clinic:clinic@127.0.0.1:5432/clinic" \
    TEST_DATABASE_URL="postgresql+psycopg://clinic:clinic@127.0.0.1:5432/clinic_test" \
    .venv/bin/python -m pytest -v
  ) > "$WORK/pytest.txt" 2>&1
  term "$WORK/pytest.txt" "$OUT/09-pytest-passing.png" "clinic-desk/backend — pytest -v"

  echo "==> git history"
  { echo '$ git log --oneline --graph --decorate'; echo; git log --oneline --graph --decorate | head -40;
    echo; echo '$ git rev-list --count HEAD'; echo; git rev-list --count HEAD; } > "$WORK/gitlog.txt"
  term "$WORK/gitlog.txt" "$OUT/13-git-history.png" "clinic-desk — commit history"

  echo "==> terraform"
  # `terraform plan` normally contacts AWS to validate credentials and to look
  # up availability zones. An override file with mock credentials plus pinned
  # zones lets the plan render offline, which is enough to prove the config is
  # valid and non-empty. The override is temporary and never committed.
  local override="$ROOT/terraform/zz_screenshot_offline_override.tf"
  cat > "$override" <<'OVERRIDE'
# TEMPORARY: written by scripts/screenshots.sh, deleted immediately after use.
provider "aws" {
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
}
OVERRIDE
  {
    echo '$ terraform -chdir=terraform validate'
    echo
    ( cd terraform && terraform validate 2>&1 | sed 's/\x1b\[[0-9;]*m//g' )
    echo
    echo '$ terraform -chdir=terraform plan   # offline check: mock credentials, zones pinned'
    echo
    ( cd terraform && terraform plan -no-color -input=false \
        -var 'availability_zones=["us-east-1a","us-east-1b"]' \
        -var-file=terraform.tfvars.example 2>&1 \
      | sed 's/\x1b\[[0-9;]*m//g' \
      | grep -E "^Plan:|will be created" | head -32 )
  } > "$WORK/terraform.txt" 2>&1
  rm -f "$override"
  term "$WORK/terraform.txt" "$OUT/17-terraform-plan.png" "clinic-desk — terraform validate + plan"

  if docker image inspect clinicdesk-backend:local >/dev/null 2>&1; then
    echo "==> docker + trivy"
    {
      echo '$ docker exec clinicdesk-backend id'; echo; docker exec clinicdesk-backend id 2>/dev/null
      echo; echo '$ docker exec clinicdesk-frontend id'; echo; docker exec clinicdesk-frontend id 2>/dev/null
    } > "$WORK/nonroot.txt"
    term "$WORK/nonroot.txt" "$OUT/11-non-root-users.png" "clinic-desk — container users"

    if command -v trivy >/dev/null 2>&1; then
      {
        echo '$ trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 <image>'
        echo
        for img in clinicdesk-backend:local clinicdesk-frontend:local; do
          echo "--- $img ---"
          trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed "$img" 2>/dev/null \
            | sed 's/\x1b\[[0-9;]*m//g' | grep -E "debian|alpine|Python  " | head -3
          trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --quiet "$img" >/dev/null 2>&1
          echo "-> exit code $?  (0 = no HIGH/CRITICAL vulnerabilities)"
          echo
        done
      } > "$WORK/trivy.txt"
      term "$WORK/trivy.txt" "$OUT/12-trivy-clean.png" "clinic-desk — Trivy security scan"
    fi
  fi
}

# ---------- Kubernetes (M8) ----------
capture_k8s() {
  echo "==> kubernetes ($INGRESS_URL)"
  if ! kubectl get ns clinicdesk >/dev/null 2>&1; then
    echo "    namespace 'clinicdesk' not found — skipping"
    return 0
  fi
  {
    echo '$ kubectl get pods -n clinicdesk'; echo; kubectl get pods -n clinicdesk
    echo; echo '$ kubectl get svc -n clinicdesk'; echo; kubectl get svc -n clinicdesk
    echo; echo '$ helm list -n clinicdesk'; echo; helm list -n clinicdesk
    echo; echo '$ kubectl get ingress -n clinicdesk'; echo; kubectl get ingress -n clinicdesk
  } > "$WORK/k8s.txt" 2>&1
  term "$WORK/k8s.txt" "$OUT/20-kubectl-resources.png" \
    "clinicdesk namespace — kubectl get pods / svc / ingress, helm list"

  local tmp="$WORK/k8s-shots"
  rm -rf "$tmp"
  node scripts/screenshots.mjs "$INGRESS_URL" "$tmp" || return 0
  mv "$tmp/01-dashboard.png"          "$OUT/21-app-via-ingress-dashboard.png"
  mv "$tmp/02-appointments.png"      "$OUT/22-app-via-ingress-appointments.png"
  mv "$tmp/06-booking-modal.png"     "$OUT/23-app-via-ingress-booking.png"
  rm -rf "$tmp"
}

# ---------- Monitoring (M9) ----------
capture_monitoring() {
  echo "==> grafana ($GRAFANA_URL)"
  node scripts/screenshot-grafana.mjs "$GRAFANA_URL" "$OUT/26-grafana-dashboard.png" || return 0

  echo "==> metrics endpoint"
  {
    echo '$ curl -s http://clinicdesk-backend-metrics:8000/metrics'
    echo
    kubectl run metrics-shot --rm -i --restart=Never -n clinicdesk \
      --image=curlimages/curl:latest --image-pull-policy=IfNotPresent --quiet -- \
      curl -s http://clinicdesk-backend-metrics:8000/metrics 2>/dev/null \
      | grep -E "^# (HELP|TYPE) http_|^http_requests_total|^http_request_duration_seconds_count" \
      | head -14
  } > "$WORK/metrics.txt"
  term "$WORK/metrics.txt" "$OUT/24-metrics-endpoint.png" "clinicdesk namespace — /metrics endpoint"
}

case "${1:-all}" in
  app)        capture_app ;;
  terminal)   capture_terminal ;;
  k8s)        capture_k8s ;;
  monitoring) capture_monitoring ;;
  all)        capture_app; capture_terminal; capture_k8s; capture_monitoring ;;
  *) echo "usage: $0 [app|terminal|k8s|monitoring|all]" >&2; exit 2 ;;
esac

echo
echo "screenshots written to $OUT"