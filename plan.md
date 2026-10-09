# DevOps Capstone Execution Plan

## Module Status
- M1 (Application): ✅ COMPLETE
- M2 (Testing): ✅ COMPLETE — 85 tests passing, ruff clean
- M3 (Git/GitHub): ✅ COMPLETE — public repo, meaningful commits, no secrets
- M4 (Docker): ✅ COMPLETE — 3 services healthy, both images non-root
- M5 (CI/CD): ✅ COMPLETE — green pipeline, SHA-tagged images in GHCR
- M6 (DevSecOps): ✅ COMPLETE — Trivy gate on both images, 0 HIGH/CRITICAL
- M7 (Terraform): ⬜ NOT STARTED
- M8 (Kubernetes + Helm): ⬜ NOT STARTED
- M9 (Observability): ⬜ NOT STARTED
- M10 (Presentation): ⬜ NOT STARTED

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
- [ ] Create `terraform/` directory with valid HCL
- [ ] VPC with 2+ public subnets
- [ ] EKS cluster with node group
- [ ] `terraform.tfvars.example` (no credentials)
- [ ] Test: init, plan, apply, destroy all work
- [ ] **BLOCKED: needs AWS credentials + region from the user before apply**

## M8: Kubernetes + Helm (15 points)
- [ ] `k8s/namespace.yaml`
- [ ] `helm/clinicdesk/` chart (Chart.yaml, values.yaml, templates)
- [ ] 2+ replicas for backend + frontend
- [ ] ClusterIP Services
- [ ] Ingress: `/` → frontend, `/api` → backend
- [ ] Test: helm upgrade --install, pods running

## M9: Observability (10 points)
- [x] Backend `/metrics` endpoint (Prometheus instrumentation already present, verified 200)
- [ ] `monitoring/` with Prometheus + Grafana values
- [ ] Verify Prometheus scraping
- [ ] Grafana dashboard showing metrics

## M10: Presentation (5 points)
- [ ] Update README with DevOps instructions
- [ ] Prepare live demo