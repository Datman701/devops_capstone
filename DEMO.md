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
helm rolls the pods onto that SHA  →  the badge in the browser changes
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
re-run `./scripts/demo-deploy.sh`.

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

### 4. Deploy the new build (1-2 min)

```bash
./scripts/demo-deploy.sh
```

With no argument it takes the current commit's short SHA — the one the pipeline
just published. It runs `helm upgrade --install` pinned to
`ghcr.io/datman701/devops_capstone/{backend,frontend}:<sha>`, waits for the
rollout, then prints the running images.

The output to point at:

```
deployment "clinicdesk-backend" successfully rolled out
deployment "clinicdesk-frontend" successfully rolled out

POD                                    IMAGE
clinicdesk-backend-...-tvrmd           ghcr.io/datman701/devops_capstone/backend:<sha>
clinicdesk-backend-...-v46j7           ghcr.io/datman701/devops_capstone/backend:<sha>
clinicdesk-frontend-...-7fdlg          ghcr.io/datman701/devops_capstone/frontend:<sha>
clinicdesk-frontend-...-sqc65          ghcr.io/datman701/devops_capstone/frontend:<sha>
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

# Observability picks up the new pods
kubectl port-forward -n monitoring svc/grafana 13000:80
# open http://localhost:13000 (admin / clinicdesk) — request rate still climbing
```

---

## If there is no cloud cluster

M7 (real AWS `apply`) is blocked. That is **not** a blocker for this demo: the
deployment half runs on the local `kind` cluster, which is a real Kubernetes API
and a real Ingress. Say so plainly rather than hiding it:

> "The cluster is `kind` running on this machine rather than EKS. The manifests
> are identical — `helm upgrade` is the same command — so the pipeline-to-
> deployment flow you're watching is the production flow. The Terraform that
> would provision the EKS cluster it should run on is in `terraform/`."

---

## Reset afterwards

```bash
# Put the cluster back on the locally-built images
helm upgrade --install clinicdesk helm/clinicdesk -n clinicdesk \
  --set images.backend.repository=clinicdesk-backend --set images.backend.tag=local \
  --set images.frontend.repository=clinicdesk-frontend --set images.frontend.tag=local
```

If you provisioned AWS for M7, the last step of the whole submission is:

```bash
terraform -chdir=terraform destroy
```

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
| M9 Observability | Grafana request rate followed by dashboard |
| M10 Docs/Demo | This runbook, plus `screenshots.md` |
| M7 Terraform | Shown as code + plan only — needs AWS creds to apply |
