# ClinicDesk

A clinic appointment booking application: a React dashboard over a FastAPI
backend and PostgreSQL. Doctors, patients and appointments with slot-conflict
protection and a status workflow.

This repository covers the application *and* its full DevOps lifecycle —
containers, a gated CI/CD pipeline with container scanning, AWS infrastructure
code, a Helm chart for Kubernetes, and Prometheus/Grafana monitoring.

**Evidence for every module is collected in [`screenshots.md`](screenshots.md).**

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite 6, React Router 7, plain CSS |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| Database | PostgreSQL 16, Alembic migrations |
| Tests | pytest + httpx (`TestClient`) |
| Containers | Multi-stage Dockerfiles, Docker Compose |
| CI/CD | GitHub Actions, GHCR, Trivy |
| IaC | Terraform (VPC + EKS) |
| Orchestration | Helm, Kubernetes, ingress-nginx |
| GitOps | ArgoCD |
| Monitoring | Prometheus, Grafana |
| Tooling | uv (Python 3.12), ruff, Node 22+ |

## What it does

- **Doctors** — roster with specialty, email and consultation fee.
- **Patients** — directory with unique phone number and optional email.
- **Appointments** — booked against a doctor and patient at a specific time,
  with these rules enforced by the API *and* the database:
  - **No double-booking.** A partial unique index
    (`uq_appointments_doctor_slot`) prevents two live appointments in the same
    doctor slot, so concurrent writes cannot race past application checks.
  - **Cancelling frees the slot.** The index excludes `cancelled` rows, so a
    cancelled time becomes bookable again.
  - **Status workflow.** `scheduled → confirmed → completed`, with `cancelled`
    and `no_show` reachable from the open states. Terminal states
    (`completed`, `cancelled`, `no_show`) cannot transition further — enforced
    identically by `PATCH /status` and `DELETE`.
  - **Availability.** `GET /api/appointments/{doctor_id}/availability` returns
    genuinely free 30-minute slots between 09:00 and 18:00.
- **Dashboard** — KPI cards, upcoming schedule, activity feed and a ranked
  doctor-load panel, all from one aggregation endpoint.

## Project layout

```text
clinic-desk/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app, middleware, Prometheus
│   │   ├── config.py            Settings (pydantic-settings)
│   │   ├── database.py          Engine, session, Base
│   │   ├── seed.py              Demo data loader
│   │   ├── models/              doctor.py, patient.py, appointment.py
│   │   ├── schemas/             Pydantic request/response models
│   │   └── api/routes/          system, directory, appointments, stats
│   ├── alembic/versions/        0001_initial_schema.py
│   ├── tests/                   conftest.py + 7 test modules
│   ├── Dockerfile               multi-stage, runs as uid 1001
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/client.js        Single fetch wrapper
│   │   ├── components/          Sidebar, Topbar, KpiCards, table, modal
│   │   ├── hooks/useClinicData.js
│   │   ├── pages/               Dashboard, Appointments, Doctors, Patients
│   │   └── styles/app.css
│   ├── Dockerfile               Node build → nginx runtime, runs as uid 101
│   └── nginx.conf
├── docker-compose.yml           Full stack: frontend, backend, PostgreSQL
├── .github/workflows/ci.yml     Tests → builds → scans → publishes to GHCR
├── helm/clinicdesk/             Chart for the Kubernetes deployment
├── k8s/namespace.yaml
├── argocd/application.yaml      ArgoCD Application — GitOps source of truth
├── monitoring/
│   ├── prometheus/values.yaml   Scrape config + alert rules
│   └── grafana/                 Datasource + provisioned dashboard
├── terraform/                   VPC with public subnets + EKS cluster
├── docs/
│   ├── screenshots/             Every submission screenshot
│   └── security.md              Trivy findings and remediations
├── demo/                        Slide deck (PPTX/PDF) and the demo video
├── screenshots.md               Screenshot index — annotated, mapped to the rubric
└── scripts/                     Dev helpers, smoke tests, screenshot tooling
```

## Running it

### The whole stack with one command

```bash
docker compose up --build
```

- Application: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>

nginx serves the built React bundle and reverse-proxies `/api` to the backend,
so the browser makes same-origin requests and no CORS configuration is needed.

Both images run as non-root users, and each declares a `HEALTHCHECK`. The
backend waits on the PostgreSQL healthcheck before starting, so it cannot race
database initialisation.

To tear down, keeping the data volume:

```bash
docker compose down
```

### Frontend and backend on the host, for development

<details>
<summary>Click to expand</summary>

**1. PostgreSQL**

```bash
docker compose up -d db
```

This also creates a separate `clinic_test` database for pytest.

**2. Backend**

```bash
cd backend
uv venv --python 3.12 .venv          # or: python3.12 -m venv .venv
uv pip install -r requirements-dev.txt

cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed         # optional demo data (--reset to wipe first)

.venv/bin/uvicorn app.main:app --reload --port 8000
```

**3. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to port 8000.

Or use the helper scripts from the repository root:

```bash
./scripts/dev-backend.sh      # detached uvicorn on :8000
./scripts/dev-frontend.sh     # detached vite on :5173
```

</details>

## CI/CD

Every push to `main`, and every pull request, runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

| Job | Does | Gate |
|---|---|---|
| `backend-test` | 85 pytest tests against a throwaway Postgres service, then `ruff check` and `ruff format --check` | Fails the run |
| `frontend-build` | `npm ci` and the Vite production build; uploads the bundle as an artifact | Fails the run |
| `docker` | Builds both images, **scans them with Trivy**, then pushes to GHCR | `needs:` both jobs above |

Nothing is built or published unless tests pass and the frontend compiles.

Images are tagged with the **full and short commit SHA** — never `latest` — so
a deployed image always maps back to exactly one commit:

```text
ghcr.io/datman701/devops_capstone/backend:<sha>
ghcr.io/datman701/devops_capstone/frontend:<sha>
```

Publishing uses the automatic `GITHUB_TOKEN`, so no registry secret is stored in
the repository. The workflow declares `packages: write` explicitly; without it
the token inherits the repository default and cannot create packages.

### Security gate

Trivy scans both images for OS-package and Python-dependency CVEs and is
configured with `exit-code: '1'`, so **a HIGH or CRITICAL finding fails the job
and the push steps never run**. Unfixed CVEs are reported but not blocking,
since there is nothing to apply.

Both images currently report **0 HIGH and 0 CRITICAL**. See
[`docs/security.md`](docs/security.md) for the findings that were remediated and
what each one meant.

## Infrastructure as code

[`terraform/`](terraform/) provisions a VPC across two availability zones with
public and private subnets, an internet gateway, workload security groups, and
an EKS cluster with a managed worker node group — 27 resources.

```bash
cd terraform
terraform init
terraform validate
terraform plan -var-file=terraform.tfvars.example
terraform apply  -var-file=terraform.tfvars.example
```

**Credentials are never in the configuration.** Terraform reads them from the
standard AWS chain (`AWS_PROFILE`, environment variables, `~/.aws/credentials`),
and `terraform.tfvars` is gitignored — only `terraform.tfvars.example` is
committed.

A NAT Gateway defaults to **off**, because at roughly USD 0.045/hour plus data
charges it is the most expensive line item in the stack. With it off, worker
nodes run in public subnets, which is fine for a throwaway cluster. Set
`enable_nat_gateway = true` for anything resembling a real deployment.

> **Clean up after yourself:** `terraform destroy` when the demonstration is
> done, so the cluster stops billing.

## Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml

kind load docker-image clinicdesk-backend:local clinicdesk-frontend:local

helm upgrade --install clinicdesk ./helm/clinicdesk \
  --namespace clinicdesk --wait
```

This deploys two backend replicas, two frontend replicas and PostgreSQL, all
behind ClusterIP Services, with an Ingress routing `/api` to the backend and
everything else to the SPA. Migrations run as an **initContainer**, so the pods
are never serving against an empty schema.

```bash
kubectl get pods -n clinicdesk
kubectl get svc  -n clinicdesk

kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80
# open http://localhost:8080
```

Watch the deployment handle a rolling update:

```bash
kubectl set image deploy/clinicdesk-backend \
  backend=clinicdesk-backend:local -n clinicdesk
kubectl rollout status deploy/clinicdesk-backend -n clinicdesk
```

## GitOps with ArgoCD

The Kubernetes deployment is declarative and Git-driven:
[`argocd/application.yaml`](argocd/application.yaml) points ArgoCD at the Helm
chart in this repository, and ArgoCD continuously reconciles the cluster to
match it — automated sync with `prune` and `selfHeal`.

```bash
kubectl create namespace argocd
kubectl apply --server-side -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl apply -f argocd/application.yaml
kubectl -n argocd get application clinicdesk      # Synced / Healthy
```

Git is the single source of truth: manual drift is reverted automatically, and a
rollback is a `git revert`. The image coordinates CI publishes are pinned in the
Application's `helm.parameters`.

```bash
kubectl -n argocd port-forward svc/argocd-server 18081:80
# open http://localhost:18081
```

The imperative `helm upgrade` commands above remain useful for local
development, but the graded deployment is driven by ArgoCD.

## Monitoring

```bash
./scripts/install-monitoring.sh
```

Installs Prometheus and Grafana from [`monitoring/`](monitor/), each with its
own values file. Prometheus discovers the API through the `prometheus.io/*`
annotations the Helm chart places on the metrics Service.

```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:80   # targets
kubectl port-forward -n monitoring svc/grafana 3000:80             # admin / clinicdesk
```

The Grafana dashboard is provisioned automatically — request rate, p95 latency,
5xx ratio and per-endpoint breakdown, with an `Endpoint` variable to filter the
panels.

`/metrics` is deliberately **not** under `/api`, because only `/api/*` is routed
through the Ingress. Metrics get their own ClusterIP Service and stay off the
public ingress.

Probe endpoints stay at the root; everything the browser uses lives under
`/api`. This split is what lets nginx and the Kubernetes Ingress route `/api/*`
to the backend and everything else to the static frontend.

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service banner |
| GET | `/health` | Liveness (never touches the DB) |
| GET | `/ready` | Readiness (verifies DB, 503 when down) |
| GET | `/metrics` | Prometheus exposition |
| GET | `/api/health` | Liveness alias for the browser |
| GET | `/api/appointments` | List; filters `status`, `doctor_id`, `patient_id`, `date_from`, `date_to`, `upcoming_only`, `skip`, `limit` |
| POST | `/api/appointments` | Book (201, 409 on slot conflict, 422 on bad input) |
| GET | `/api/appointments/{id}` | Fetch one |
| PUT | `/api/appointments/{id}` | Update / reschedule |
| PATCH | `/api/appointments/{id}/status` | Status transition |
| DELETE | `/api/appointments/{id}` | Cancel (204, frees the slot) |
| GET | `/api/appointments/{id}/history` | Current status + allowed next states |
| GET | `/api/appointments/{doctor_id}/availability` | Free slots for a day |
| GET | `/api/appointments/stats` | Dashboard aggregation |
| GET/POST | `/api/doctors`, `/api/doctors/{id}` | Doctor roster |
| GET/POST | `/api/patients`, `/api/patients/{id}` | Patient directory |

Example:

```bash
curl -X POST http://localhost:8000/api/appointments \
  -H 'Content-Type: application/json' \
  -d '{
        "doctor_id": 1,
        "patient_id": 1,
        "scheduled_at": "2026-11-04T10:30:00+05:30",
        "duration_minutes": 30,
        "reason": "New patient consult"
      }'
```

## Database schema

```text
doctors      id, full_name, specialty, email (unique), consultation_fee,
             is_active, created_at

patients     id, full_name, phone (unique), email, date_of_birth, created_at

appointments id, doctor_id → doctors.id (RESTRICT),
             patient_id → patients.id (RESTRICT),
             scheduled_at (tz), duration_minutes, reason, notes,
             status (enum: scheduled|confirmed|completed|cancelled|no_show),
             created_at, updated_at
```

Indexes: `uq_appointments_doctor_slot` (partial unique, the double-booking
guard), `ix_appointments_status_scheduled_at`, plus foreign-key and
`scheduled_at` indexes.

Migrations are managed by Alembic:

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade base
```

## Tests

```bash
cd backend
.venv/bin/python -m pytest -v
```

85 tests across 7 modules, covering health/readiness/metrics, appointment CRUD,
status transitions, slot conflicts, request validation, filters and pagination,
availability, the stats aggregation, and the doctors/patients directories.

Tests run against the dedicated **`clinic_test`** database — never the
development `clinic` database. `conftest.py` applies the Alembic migrations
once per session (so the migrations themselves are exercised) and gives each
test a session wrapped in an outer transaction that is always rolled back, so
tests cannot leak rows into each other.

```bash
# useful during development
.venv/bin/python -m pytest -v
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
.venv/bin/ruff check app tests
.venv/bin/ruff format app tests
```

## Notes on a few deliberate decisions

- **Slot conflicts are guarded twice.** The service checks for an existing
  appointment and returns `409`, but the partial unique index is the real
  guarantee because it also holds under concurrent inserts.
- **`DELETE` cancels rather than deletes,** preserving the audit trail used by
  the activity feed, and freeing the slot for rebooking.
- **Email validation allows reserved domains** (`.test`, `.example`) because
  this is a demo and test environment; see `app/schemas/types.py`.
- **`/health` never queries the database** so a database outage cannot cause
  Kubernetes to kill otherwise-healthy pods. `/ready` is the endpoint that
  reports database connectivity.
- **Tests never touch dev data,** which keeps `pytest` safe to run at any time.

## Smoke testing

```bash
node scripts/e2e-ui-smoke.mjs   # books an appointment through the real UI
```

## Status

| Area | State | Evidence |
|---|---|---|
| Backend + REST API | ✅ Done | [`screenshots.md` §1](screenshots.md#m1--application-10-points) |
| Database + Alembic | ✅ Done | M1 |
| Tests | ✅ Done — 85 passing | [§2](screenshots.md#m2--testing-10-points) |
| Frontend dashboard | ✅ Done — responsive | §1 |
| Docker / Compose | ✅ Done — 3 healthy services, non-root | [§4](screenshots.md#m4--docker-10-points) |
| CI/CD + GHCR | ✅ Done — green pipeline, SHA tags | [§5](screenshots.md#m5--cicd-15-points) |
| Security scanning | ✅ Done — 0 HIGH / 0 CRITICAL | [§6](screenshots.md#m6--devsecops-5-points) |
| Terraform (VPC + EKS) | ✅ Done — applied to AWS, then destroyed and verified clean | [§7](screenshots.md#m7--terraform-15-points) |
| Kubernetes + Helm | ✅ Done — 5 pods Running via Ingress | [§8](screenshots.md#m8--kubernetes--helm-15-points) |
| GitOps (ArgoCD) | ✅ Done — application Synced / Healthy | [above](#gitops-with-argocd) |
| Observability | ✅ Done — target UP, 9 live Grafana panels | [§9](screenshots.md#m9--observability-10-points) |

The Terraform stack was applied against a real AWS account and then destroyed,
so nothing is left billing.