# DevOps Capstone Execution Plan

## Module Status
- M1 (Application): ✅ COMPLETE
- M2 (Testing): ✅ COMPLETE — 85 tests passing, ruff clean
- M3 (Git/GitHub): ✅ COMPLETE — public repo, meaningful commits, no secrets
- M4 (Docker): ✅ COMPLETE — 3 services healthy, both images non-root
- M5 (CI/CD): ⬜ NOT STARTED
- M6 (DevSecOps): ⬜ NOT STARTED
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
- [ ] Create `.github/workflows/ci.yml`
- [ ] Job: pytest tests (fail pipeline on error)
- [ ] Job: Frontend build
- [ ] Job: Build both Docker images
- [ ] Job: Push to GHCR with SHA tags
- [ ] Trigger on push to `main`

## M6: DevSecOps (5 points)
- [ ] Add Trivy scan step for both images
- [ ] Configure pipeline to fail on HIGH/CRITICAL CVEs
- [ ] Document one CVE finding or clean scan

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