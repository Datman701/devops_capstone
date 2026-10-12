#!/usr/bin/env bash
#
# Installs the M9 monitoring stack (Prometheus + Grafana) into the current
# Kubernetes cluster and waits for both to be ready.
#
#   ./scripts/install-monitoring.sh
#
# The upstream chart downloads are fetched to a local directory first, because
# pulling them straight from GitHub during `helm install` is unreliable on a
# flaky link.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${MONITORING_CACHE_DIR:-/tmp/opencode/monitoring}"
NS="${MONITORING_NAMESPACE:-monitoring}"

PROMETHEUS_VERSION="${PROMETHEUS_VERSION:-29.36.1}"
GRAFANA_VERSION="${GRAFANA_VERSION:-10.5.15}"

PROMETHEUS_URL="https://github.com/prometheus-community/helm-charts/releases/download/prometheus-${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.tgz"
GRAFANA_URL="https://github.com/grafana/helm-charts/releases/download/grafana-${GRAFANA_VERSION}/grafana-${GRAFANA_VERSION}.tgz"

mkdir -p "$CACHE"

fetch() {
  local url="$1" dest="$2"
  if [[ -s "$dest" ]]; then
    echo "using cached $(basename "$dest")"
    return
  fi
  echo "downloading $(basename "$dest")"
  curl -sSL --retry 3 --retry-delay 2 --max-time 180 -o "$dest" "$url"
}

fetch "$PROMETHEUS_URL" "$CACHE/prometheus.tgz"
fetch "$GRAFANA_URL" "$CACHE/grafana.tgz"

echo
echo "==> Prometheus"
helm upgrade --install prometheus "$CACHE/prometheus.tgz" \
  --namespace "$NS" --create-namespace \
  --values "$ROOT/monitoring/prometheus/values.yaml" \
  --wait --timeout 10m

echo
echo "==> Grafana"
# The dashboard JSON is injected from disk so the file under
# monitoring/grafana/dashboards/ stays the single source of truth. The key
# contains a dot, so it is escaped for Helm's --set-file parser.
helm upgrade --install grafana "$CACHE/grafana.tgz" \
  --namespace "$NS" --create-namespace \
  --values "$ROOT/monitoring/grafana/values.yaml" \
  --set-file "dashboards.clinicdesk.clinicdesk-api\.json.json=${ROOT}/monitoring/grafana/dashboards/clinicdesk-api.json" \
  --wait --timeout 10m

echo
echo "==> Verifying the scrape target"
for _ in $(seq 1 30); do
  up="$(kubectl run prom-query --rm -i --restart=Never -n "$NS" \
        --image=curlimages/curl:latest --image-pull-policy=IfNotPresent --quiet -- \
        curl -s 'http://prometheus-server:9090/api/v1/query?query=up%7Bjob%3D%22clinicdesk-api%22%7D' 2>/dev/null \
        | grep -o '"value":\[[^]]*\]' | head -1)"
  if [[ "$up" == *"1"* ]]; then
    echo "Prometheus reports clinicdesk-api UP"
    break
  fi
  sleep 10
done

echo
kubectl get pods -n "$NS"
echo
echo "Prometheus: kubectl port-forward -n $NS svc/prometheus-server 9090:80"
echo "Grafana:    kubectl port-forward -n $NS svc/grafana 3000:80   (admin / clinicdesk)"