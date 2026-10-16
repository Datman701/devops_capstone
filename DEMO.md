# Live Demo Runbook — M10

The M10 rubric asks for one thing:

> **Live demo: commit a change, watch the pipeline run, see the deployment update.**

This is the script for that. It takes about eight minutes.

---

## The idea

The UI now shows the **commit SHA it was built from** as a badge next to the page
title. That turns "the deployment updated" from a claim into something visible on
screen:

```
commit a change  →  Actions builds an image tagged with the new SHA  →
ArgoCD syncs that SHA onto the cluster  →  the badge in the browser changes
```

No screenshots can fake that, because the number on screen is produced by the
pipeline from the commit you just pushed.

---

## Before the demo — pre-flight

Run this five minutes ahead. Everything must be green **before** you start
talking, so the live steps are only the interesting ones.

```bash
# 1. Cluster is up (kind + ingress + the app)
kubectl get pods -n clinicdesk          # 5 pods Running
kubectl get pods -n ingress-nginx       # controller Running
kubectl get pods -n monitoring          # prometheus + grafana Running
kubectl get pods -n argocd              # argo-cd pods Running
kubectl -n argocd get application clinicdesk   # Synced / Healthy

# 2. Last pipeline run is green
gh run list --limit 3

# 3. GHCR still has the images
docker pull ghcr.io/datman701/devops_capstone/frontend:$(git rev-parse --short HEAD)

# 4. Port-forward the Ingress, leave it running in its own terminal
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 18080:80

# 5. Sanity-check the app in a browser
xdg-open http://localhost:18080
```

If `monitoring` or `ingress-nginx` pods are missing, the cluster was recreated —
reinstall with `./scripts/install-monitoring.sh` and the ingress manifest, then
re-apply the ArgoCD Application: `kubectl apply -f argocd/application.yaml`.

> **Cluster was asleep?** `kind` clusters stop when Docker restarts. Start it
> with `docker start clinicdesk-control-plane`, then wait for the API:
> `kubectl wait --for=condition=Ready node/clinicdesk-control-plane --timeout=120s`.

---

## The demo — step by step

### 1. Show the running app (30 s)

Open `http://localhost:18080`. Point at the badge next to the **Dashboard**
title — note the SHA on screen and say it out loud. That is the commit the
running pods were built from.

> "Everything you're about to see is deployed in Kubernetes, not mocked. That
> badge is the commit SHA this image was built from."

### 2. Make a real change (1 min)

Change the dashboard subtitle — small, visible, and impossible to mistake for
cached content.

```bash
# Edit the dashboard subtitle in frontend/src/App.jsx, line ~13:
#   '/': { title: 'Dashboard', subtitle: 'Clinic-wide appointment overview' },
git add -A
git commit -m "feat(ui): update dashboard subtitle for the live demo"
git push origin main
```

### 3. Watch the pipeline (3-4 min)

```bash
gh run watch
```

Walk through the jobs as they light up, mapping each to a rubric item:

| Job on screen | What it proves |
|---------------|----------------|
| **backend tests** | M2/M5 — pytest gates the build; a red test stops everything |
| **frontend build** | M5 — Vite bundles the SPA |
| **build images** | M5 — both images built |
| **trivy scan** | M6 — HIGH/CRITICAL fails the job |
| **push to GHCR** | M5 — images published with the commit SHA, never `latest` |

Say explicitly: **the scan runs before the push**, so a vulnerable image can
never reach the registry.

### 4. Let ArgoCD deploy the new build (1-2 min)

Deployment is GitOps, not a manual `helm upgrade`. The image coordinates the
pipeline published live in [`argocd/application.yaml`](argocd/application.yaml).

```bash
# Point the two image tags at the SHA the pipeline just published:
#   spec.source.helm.parameters → images.backend.tag / images.frontend.tag
$EDITOR argocd/application.yaml
git add argocd/application.yaml
git commit -m "chore(gitops): deploy <sha>"
git push origin main

# Hand the new desired state to ArgoCD
kubectl apply -f argocd/application.yaml
```

ArgoCD renders `helm/clinicdesk` from Git and rolls the pods onto the new SHA —
no imperative command touches the cluster. Watch it converge:

```bash
kubectl -n argocd get application clinicdesk -w      # Synced / Healthy
```

### 5. See the deployment update (30 s)

Reload `http://localhost:18080`. Two things changed:

1. The **subtitle** is your new text.
2. The **badge** now shows the **new** commit SHA.

> "Same URL, new code. The number on the badge is the commit I pushed two
> minutes ago — that is the pipeline end to end."

### 6. Optional extras, if time allows

```bash
# Zero-downtime: old pods stayed up until new ones were Ready
kubectl -n clinicdesk rollout history deploy/clinicdesk-frontend

# ArgoCD UI — the synced application and its Git source
kubectl port-forward -n argocd svc/argocd-server 18081:80
# open http://localhost:18081 — the app card shows Synced / Healthy

# Observability picks up the new pods
kubectl port-forward -n monitoring svc/grafana 13000:80
# open http://localhost:13000 (admin / clinicdesk) — request rate still climbing
```

---

## About the cluster

The deployment runs on a local `kind` cluster — a real Kubernetes API server and
a real Ingress, not a mock. ArgoCD syncs the very same Helm chart that the
Terraform-provisioned EKS cluster (in [`terraform/`](terraform/)) would run; only
the location of the control plane differs.

---

## Reset afterwards

```bash
# Return ArgoCD to the pinned SHA: edit the tags in argocd/application.yaml, then
kubectl apply -f argocd/application.yaml
```

The Terraform stack was applied and then destroyed, so nothing is left billing.
See [M7 apply and destroy](plan.md#m7-apply-and-destroy).

---

## Quick rubric map

| Rubric item | Where it shows in this demo |
|-------------|-----------------------------|
| M1 App | Browser, live data through the Ingress |
| M2 Tests | `backend tests` job, green gate |
| M3 Git | The commit you just pushed with a real message |
| M4 Docker | Images pulled and running as non-root pods |
| M5 CI/CD | The whole pipeline, SHA tags in the push step |
| M6 DevSecOps | Trivy job failing the build before the push |
| M8 Kubernetes | `kubectl get pods`, rolling update, Ingress routing |
| GitOps | ArgoCD application Synced / Healthy — Git is the source of truth |
| M9 Observability | Grafana request rate followed by dashboard |
| M10 Docs/Demo | This runbook, plus `screenshots.md` |
| M7 Terraform | Infra as code + plan; applied to AWS, then destroyed |
