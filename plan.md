# DevOps Capstone Execution Plan

## Module Status
- M1 (Application): ✅ COMPLETE
- M2 (Testing): ✅ COMPLETE — 85 tests passing, ruff clean
- M3 (Git/GitHub): ✅ COMPLETE — public repo, meaningful commits, no secrets
- M4 (Docker): ✅ COMPLETE — 3 services healthy, both images non-root
- M5 (CI/CD): ✅ COMPLETE — green pipeline, SHA-tagged images in GHCR
- M6 (DevSecOps): ✅ COMPLETE — Trivy gate on both images, 0 HIGH/CRITICAL
- M7 (Terraform): 🟡 CODE COMPLETE — 27 resources planned & validated; needs a real `apply` for the console screenshots
- M8 (Kubernetes + Helm): ✅ COMPLETE — 5 pods Running via Helm on kind
- M9 (Observability): ✅ COMPLETE — Prometheus scraping, Grafana dashboard live
- M10 (Presentation + Docs): ✅ COMPLETE — README rewritten, docs/screenshots.md indexes all 24 images

## Application polish (completed)
- [x] Appointments filter requires an explicit **Apply filter** action (draft vs applied state)
- [x] Fixed unbounded refetch loop in `useAppointments` (dep keyed on filters object identity)
- [x] Removed duplicated `useReferenceData`/`useAppointments` copies inlined in `DashboardPage`
- [x] Removed spurious unconditional error banner on the dashboard
- [x] Added `scripts/verify-filter.mjs` browser check for the filter contract

## M4: Docker (10 points)
- [x] Create `backend/Dockerfile` (multi-stage, non-root, Python 3.12)
- [x] Create `frontend/Dockerfile` (Node build → Nginx runtime, non-root)
- [x] Update `docker-compose.yml` to include frontend + backend + postgres
- [x] Test: `docker compose up --build` — all 3 services running
- [x] Verify images run as non-root (backend `uid=1001(app)`, frontend `uid=101(nginx)`)

### M4 verification notes
- Frontend published on `:3000`; nginx proxies `/api` → `backend:8000`; SPA routes fall through to `index.html`.
- Backend waits on the db healthcheck (`service_healthy`) to avoid racing Postgres init.
- Both images declare `HEALTHCHECK`. `/health` is liveness-only so a DB outage cannot cause a restart loop; `/ready` is the dependency gate.
- `.dockerignore` keeps `.venv/`, `node_modules/` and `.env` out of the build context.
- `docker compose up --build` was verified against the built stack; filter contract re-verified through nginx on `:3000`.

## M5: CI/CD (15 points)
- [x] Create `.github/workflows/ci.yml`
- [x] Job: pytest tests (fail pipeline on error) — 85 tests against a throwaway Postgres service
- [x] Job: Frontend build (`npm ci` + `vite build`)
- [x] Job: Build both Docker images
- [x] Job: Push to GHCR with SHA tags — verified pullable at `ghcr.io/datman701/devops_capstone/{backend,frontend}`
- [x] Trigger on push to `main`

### M5 pipeline
Three jobs, gated in order: `backend-test` → `frontend-build` → `docker`. The image job
`needs:` both test jobs, so nothing is built or published unless tests and the frontend
build pass. Ruff runs as an extra lint gate.

Images are tagged with the full and short commit SHA. No `:latest` tag is ever published.

Fixes required to reach green, each recorded in its own commit:
- Trivy action referenced as `0.28.0`; its release tags are `v`-prefixed.
- GHCR rejects uppercase in the repository path, so the namespace is lowercased in the
  derive-tags step (owner is `Datman701`) rather than hardcoded.
- The workflow needed an explicit `permissions: {contents: read, packages: write}` block,
  otherwise `GITHUB_TOKEN` inherits the repo default and cannot create packages.

## M6: DevSecOps (5 points)
- [x] Add Trivy scan step for both images
- [x] Configure pipeline to fail on HIGH/CRITICAL CVEs (`exit-code: '1'`, `ignore-unfixed: true`)
- [x] Document CVE findings — see [`docs/security.md`](docs/security.md)

### M6 findings and remediation
First run failed on its own gate, as intended: **7 HIGH** in backend, **45 (43 HIGH, 2 CRITICAL)** in frontend.

| Finding | Fix |
|---|---|
| starlette ×3 | FastAPI 0.115.6 → 0.143.0 (pulls starlette 1.7.0) |
| urllib3 ×2 | pinned `urllib3==2.8.0` |
| msgpack GHSA-6v7p-g79w-8964 | gone with Alembic 1.14.0 → 1.20.0 |
| setuptools CVE-2025-47273 | pip removed from runtime image |
| frontend 45 Alpine CVEs | `nginx:1.27-alpine` (3.21) → pinned `nginx:1.30.5-alpine` (3.24) |
| libexpat, pcre2, tiff | `apk upgrade --no-cache` |

The pip finding needed more than a version bump: `pip/_vendor` ships its own msgpack
1.1.2 / urllib3 2.7.0 / setuptools 70.3.0, which is what Trivy read, and upgrading
setuptools never touches those copies. Stripping pip from the runtime image removes
them honestly and drops ~12 MB.

Also required: `prometheus-fastapi-instrumentator` 7.0.0 → 8.1.0, because 7.x crashes on
FastAPI 0.14x's internal `_IncludedRouter`. This broke 84/85 tests until fixed.

**Final state: both images report 0 HIGH and 0 CRITICAL.**

## M7: Terraform (15 points)
- [x] Create `terraform/` directory with valid HCL (`versions.tf`, `variables.tf`, `vpc.tf`, `security.tf`, `eks.tf`, `outputs.tf`)
- [x] VPC with 2+ public subnets — plus private subnets and an internet gateway
- [x] EKS cluster with a managed worker node group
- [x] `terraform.tfvars.example` (no credentials anywhere in the config)
- [x] `terraform init` completes — provider `hashicorp/aws v5.100.0`
- [x] `terraform validate` passes
- [x] `terraform plan` is non-empty and error-free — **27 resources**
- [ ] `terraform apply` against a real account — **needs AWS credentials**
- [ ] `terraform destroy` — run after the apply

### M7 notes
Credentials are never declared in HCL; Terraform reads the standard AWS chain.
`terraform.tfvars` is gitignored and only the `.example` is committed, because
the grading team rejects submissions containing credentials in their history.

A NAT Gateway defaults to **off**: at roughly USD 0.045/hour plus data charges
it is the most expensive item in the stack, and the nodes do not need private
egress for a demo cluster.

`plan` is verifiable offline by writing a temporary provider override with
mock credentials and pinning `availability_zones` — that also avoids the
availability-zone lookup, which is the one data source that would otherwise
require a live API call. `scripts/screenshots.sh` does this and removes the
override immediately afterwards.

Validation caught three real errors that would have failed at apply time:
an invalid `eks_odr` block, `policy_associations` used as a nested block on
`aws_eks_access_entry` (it is a separate resource in provider v5), and
`type = "NODE_GROUP"`, which is not a valid access-entry type.

## M8: Kubernetes + Helm (15 points)
- [x] `k8s/namespace.yaml` — applies cleanly
- [x] `helm/clinicdesk/` chart (Chart.yaml, values.yaml, templates)
- [x] 2+ replicas for backend + frontend (2 each, `maxUnavailable: 0` rolling update)
- [x] ClusterIP Services — backend, frontend, postgres, plus a metrics Service
- [x] Ingress: `/api` → backend, `/` → frontend
- [x] Test: `helm upgrade --install` deploys cleanly; all 5 pods Running

### M8 verification
Deployed to a local `kind` cluster with `helm upgrade --install clinicdesk ./helm/clinicdesk
--namespace clinicdesk --wait`. Result: 5/5 pods Running (2 backend, 2 frontend, 1 postgres),
all ClusterIP Services healthy, ingress-nginx controller routing both paths, and the full
appointment filter contract re-verified in a real browser **through the Ingress**.

Design decisions worth knowing:
- **Migrations run as an initContainer.** Without it the pods boot against an empty
  database and `/ready` fails until someone runs `alembic` by hand. It waits for
  PostgreSQL to accept connections first, then runs `alembic upgrade head`.
- **Liveness uses `/health`, readiness uses `/ready`.** `/health` never touches the
  database, so a database outage cannot make Kubernetes restart every healthy API pod.
- **The nginx config is templated by the chart.** The image ships a Compose config
  pointing at the literal host `backend`; in Kubernetes the Service name depends on the
  release, so a ConfigMap renders the main `nginx.conf` with the correct upstream.
- **readOnlyRootFilesystem** is on for both app containers. That forced the nginx pid file
  and every temp path onto a `/tmp` emptyDir, which is only settable in the main
  nginx.conf — hence mounting the whole file rather than just `conf.d`.
- **A hostless Ingress rule** is included alongside the named `clinicdesk.local` host so
  the app is reachable on kind/minikube, where no DNS entry exists.
- **Pod anti-affinity is `preferred`, not required**, so replicas spread across nodes but
  still schedule on a single-node cluster instead of leaving one Pending.


## M9: Observability (10 points)
- [x] Backend `/metrics` endpoint (Prometheus instrumentation already present, verified 200)
- [x] `monitoring/` with Prometheus + Grafana values files
- [x] Verify Prometheus scraping — `clinicdesk-api` target reports UP
- [x] Grafana dashboard showing live metrics — 9 panels, all populated

### M9 verification
Installed with `./scripts/install-monitoring.sh`, which fetches the upstream chart tarballs
to a local cache first (`helm install` pulling straight from GitHub proved unreliable on this
link), then applies `monitoring/prometheus/values.yaml` and `monitoring/grafana/values.yaml`.

Prometheus discovers the API through the `prometheus.io/scrape` annotations the app chart
already puts on `clinicdesk-backend-metrics`. `/metrics` is deliberately *not* under `/api`,
because only `/api/*` is routed through the Ingress — so metrics get their own ClusterIP
Service that stays off the public Ingress.

Grafana gets a provisioned Prometheus datasource and a pre-built dashboard
(`monitoring/grafana/dashboards/clinicdesk-api.json`, injected via `--set-file` so the JSON
stays the single source of truth rather than being duplicated as inline YAML). Panels cover
target health, request rate, p95 latency, 5xx ratio and per-endpoint latency, with an
`Endpoint` template variable to filter them.

Two things the work surfaced:
- The 5xx ratio panel initially read **No data**, because when there are no 5xx series the
  numerator returns an empty vector rather than 0. Fixed with `or vector(0)`.
- `scripts/screenshot-grafana.mjs` asserts panels actually rendered before writing the
  image, so a broken datasource can never produce a pretty but empty screenshot. It caught a
  stale port-forward after a pod replacement, which is exactly what it is for.

## M10: Presentation (5 points)
- [x] Rewrite `README.md` — Docker, CI/CD, Terraform, Kubernetes and monitoring sections, refreshed project layout and status table
- [x] `docs/screenshots.md` — every screenshot in one place, annotated with what it shows and which rubric item it satisfies
- [x] `scripts/screenshots.sh` — regenerates the whole screenshot set (`app`, `terminal`, `k8s`, `monitoring` or `all`)
- [ ] Live demo: commit a change, watch the pipeline run, see the deployment update