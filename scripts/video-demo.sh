#!/usr/bin/env bash
#
# ClinicDesk video-demo helper.
#
#   ./scripts/video-demo.sh preflight
#   ./scripts/video-demo.sh change "Appointments, deployed by the pipeline"
#   ./scripts/video-demo.sh wait-ci
#   ./scripts/video-demo.sh deploy
#   ./scripts/video-demo.sh status
#   ./scripts/video-demo.sh stop
#
# preflight  seeds demo data and starts the four port-forwards used in the video.
# change     edits the dashboard subtitle, commits and pushes (triggers CI).
# wait-ci    waits for the pipeline run for the current branch to finish.
# deploy     pins the new image SHA in ArgoCD, pushes, applies and waits for sync.
# status     prints everything the video shows.
# stop       stops the port-forwards started by preflight.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NS="${NS:-clinicdesk}"
APP="${APP:-clinicdesk}"
REGISTRY="ghcr.io"
SLUG="$(git remote get-url origin | sed -E 's#.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##' | tr '[:upper:]' '[:lower:]')"
RUN_DIR="/tmp/clinicdesk-video"
mkdir -p "$RUN_DIR"

bold() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

require_main()  { [[ "$(git branch --show-current)" == "main" ]] || die "not on main"; }
require_clean() { [[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "working tree is dirty — commit or stash first"; }

start_forward() { # name ns svc local_port remote_port
  local name="$1" ns="$2" svc="$3" local_port="$4" remote="$5"
  local log="$RUN_DIR/$name.log" pidfile="$RUN_DIR/$name.pid"

  if ss -ltn 2>/dev/null | grep -q ":$local_port "; then
    ok "$name already on :$local_port"
    return
  fi
  setsid nohup kubectl -n "$ns" port-forward "svc/$svc" "$local_port:$remote" \
    >"$log" 2>&1 </dev/null &
  echo $! >"$pidfile"
  for _ in $(seq 1 40); do
    if grep -q "Forwarding from" "$log" 2>/dev/null; then break; fi
    sleep 0.25
  done
  ok "$name -> http://localhost:$local_port"
}

cmd_preflight() {
  require_main

  bold "Cluster"
  kubectl -n "$NS" get pods
  local ready total
  ready=$(kubectl -n "$NS" get pods --no-headers | awk '{split($2,a,"/"); if (a[1]==a[2] && $3=="Running") c++} END{print c+0}')
  total=$(kubectl -n "$NS" get pods --no-headers | wc -l)
  [[ "$ready" -eq "$total" && "$total" -ge 5 ]] || die "only $ready/$total pods Ready"
  ok "$ready/$total pods Ready"

  bold "ArgoCD"
  local state
  state=$(kubectl -n argocd get application "$APP" -o jsonpath='{.status.sync.status}/{.status.health.status}')
  [[ "$state" == "Synced/Healthy" ]] || die "ArgoCD is $state"
  ok "Synced/Healthy"

  bold "Seed demo data"
  kubectl -n "$NS" exec deploy/clinicdesk-backend -- python -m app.seed --reset | tail -2

  bold "Port-forwards"
  start_forward ingress    ingress-nginx ingress-nginx-controller 18080 80
  start_forward argocd     argocd        argocd-server            18081 80
  start_forward prometheus monitoring    prometheus-server        19090 80
  start_forward grafana    monitoring    grafana                  13000 80

  bold "Smoke checks"
  [[ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/)" == "200" ]] || die "app not reachable"
  ok "app 200"
  curl -s http://localhost:18080/api/health | grep -q '"status":"ok"' || die "API health failed"
  ok "API health ok"
  curl -s http://localhost:19090/-/healthy | grep -q Healthy || die "Prometheus not healthy"
  ok "Prometheus healthy"
  curl -s -u admin:clinicdesk http://localhost:13000/api/health | grep -q ok || die "Grafana not healthy"
  ok "Grafana healthy"

  bold "Ready"
  printf '  App:        http://localhost:18080\n'
  printf '  ArgoCD:     http://localhost:18081   admin / %s\n' \
    "$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
  printf '  Prometheus: http://localhost:19090/targets\n'
  printf '  Grafana:    http://localhost:13000   admin / clinicdesk\n'
  printf '  Repo HEAD:  %s\n' "$(git rev-parse --short HEAD)"
  printf '  Deployed:   %s\n' \
    "$(kubectl -n "$NS" get deploy clinicdesk-frontend -o jsonpath='{.spec.template.spec.containers[0].image}' | sed 's/.*://')"
}

cmd_change() {
  require_main; require_clean
  local subtitle="${1:-Appointments, deployed by the pipeline}"
  local file="frontend/src/App.jsx"

  sed -i -E "13s|subtitle: '[^']*'|subtitle: '${subtitle}'|" "$file"
  [[ -n "$(git diff --name-only -- "$file")" ]] || die "no change — the subtitle is already \"$subtitle\""

  git --no-pager diff -- "$file"
  git add "$file"
  git commit -m "feat(ui): update dashboard subtitle for the live demo"
  git push origin main

  bold "Pushed — pipeline starting"
  local url="" i
  for i in $(seq 1 20); do
    url=$(gh run list --commit "$(git rev-parse HEAD)" -L 1 --json url --jq '.[0].url' 2>/dev/null || true)
    [[ -n "$url" && "$url" != "null" ]] && break
    sleep 2
  done
  printf '  Run: %s\n' "${url:-check GitHub Actions}"
}

cmd_wait_ci() {
  require_main
  bold "Waiting for the pipeline (this takes ~4 minutes)"
  local run_id
  run_id=$(gh run list --branch main -L 1 --json databaseId --jq '.[0].databaseId')
  gh run watch "$run_id" --exit-status
  gh run list -L 1
}

cmd_deploy() {
  require_main; require_clean

  local sha full status conclusion
  sha="${1:-$(git rev-parse --short HEAD)}"
  full="$(git rev-parse "$sha")"
  sha="$(git rev-parse --short "$sha")"

  status=$(gh run list --commit "$full" -L 1 --json status --jq '.[0].status' 2>/dev/null || echo missing)
  conclusion=$(gh run list --commit "$full" -L 1 --json conclusion --jq '.[0].conclusion' 2>/dev/null || echo "")
  [[ "$status" == "completed" && "$conclusion" == "success" ]] \
    || die "CI for $sha is ${status}/${conclusion} — run: ./scripts/video-demo.sh wait-ci"
  ok "CI green for $sha"

  docker manifest inspect "$REGISTRY/$SLUG/frontend:$sha" >/dev/null 2>&1 \
    || die "frontend image $sha is not in GHCR yet"
  docker manifest inspect "$REGISTRY/$SLUG/backend:$sha" >/dev/null 2>&1 \
    || die "backend image $sha is not in GHCR yet"
  ok "both images published for $sha"

  sed -i -E "s|(value: \")[0-9a-f]{7,40}(\")|\1$sha\2|g" argocd/application.yaml
  git --no-pager diff -- argocd/application.yaml
  git add argocd/application.yaml
  git commit -m "chore(gitops): deploy $sha"
  git push origin main

  kubectl apply -f argocd/application.yaml

  bold "Waiting for ArgoCD"
  local state image
  for _ in $(seq 1 100); do
    state=$(kubectl -n argocd get application "$APP" -o jsonpath='{.status.sync.status}/{.status.health.status}')
    image=$(kubectl -n "$NS" get deploy clinicdesk-frontend -o jsonpath='{.spec.template.spec.containers[0].image}')
    if [[ "$state" == "Synced/Healthy" && "$image" == *":$sha" ]]; then break; fi
    sleep 3
  done
  [[ "${image:-}" == *":$sha" ]] || die "deployment did not roll to $sha"

  kubectl -n "$NS" rollout status deploy/clinicdesk-backend --timeout=180s
  kubectl -n "$NS" rollout status deploy/clinicdesk-frontend --timeout=180s

  bold "Deployed"
  kubectl -n "$NS" get deploy \
    -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image'
  printf '\n  Reload http://localhost:18080 — the badge must now read %s\n' "$sha"
}

cmd_status() {
  bold "Pods";     kubectl -n "$NS" get pods
  bold "Services"; kubectl -n "$NS" get svc
  bold "Ingress";  kubectl -n "$NS" get ingress
  bold "ArgoCD";   kubectl -n argocd get application "$APP"
  bold "Images";   kubectl -n "$NS" get deploy \
    -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image'
  bold "Data"
  curl -s http://localhost:18080/api/appointments/stats \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"  appointments: {d['total']} | doctors: {d['active_doctors']} | patients: {d['active_patients']}\")"
}

cmd_stop() {
  local f
  for f in "$RUN_DIR"/*.pid; do
    [[ -f "$f" ]] || continue
    kill "$(cat "$f")" 2>/dev/null || true
    rm -f "$f"
  done
  ok "port-forwards stopped"
}

case "${1:-}" in
  preflight) shift; cmd_preflight "$@" ;;
  change)    shift; cmd_change "$@" ;;
  wait-ci)   shift; cmd_wait_ci "$@" ;;
  deploy)    shift; cmd_deploy "$@" ;;
  status)    shift; cmd_status "$@" ;;
  stop)      shift; cmd_stop "$@" ;;
  *)
    echo "usage: $0 {preflight|change [subtitle]|wait-ci|deploy [sha]|status|stop}"
    exit 1 ;;
esac
