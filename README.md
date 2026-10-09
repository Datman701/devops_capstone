# ClinicDesk

A clinic appointment booking application: a React dashboard over a FastAPI
backend and PostgreSQL. Doctors, patients and appointments with slot-conflict
protection and a status workflow.

This repository currently covers the **application layer** (backend, database,
frontend, tests). The DevOps layers — Docker, CI/CD, Terraform, Kubernetes, Helm
and monitoring — are added on top of this structure.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite 6, React Router 7, plain CSS |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| Database | PostgreSQL 16, Alembic migrations |
| Tests | pytest + httpx (`TestClient`) |
| Tooling | uv (Python 3.12), ruff, Node 20+ |

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
│   └── pytest.ini
├── frontend/
│   └── src/
│       ├── api/client.js        Single fetch wrapper
│       ├── components/          Sidebar, Topbar, KpiCards, table, modal
│       ├── hooks/useClinicData.js
│       ├── pages/               Dashboard, Appointments, Doctors, Patients
│       └── styles/app.css
├── scripts/                     dev helpers + smoke tests
└── docker-compose.yml           PostgreSQL for local development
```

## Running locally

### 1. Start PostgreSQL

```bash
docker compose up -d db
```

This also creates a separate `clinic_test` database for pytest.

### 2. Backend

```bash
cd backend
uv venv --python 3.12 .venv          # or: python3.12 -m venv .venv
uv pip install -r requirements-dev.txt

cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed         # optional demo data (--reset to wipe first)

.venv/bin/uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/health>
- Readiness: <http://localhost:8000/ready>
- Metrics: <http://localhost:8000/metrics>

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

Or use the helper scripts from the repository root:

```bash
./scripts/dev-backend.sh      # detached uvicorn on :8000
./scripts/dev-frontend.sh     # detached vite on :5173
```

## API

Probe endpoints stay at the root; everything the browser uses lives under
`/api`. This split is what lets Nginx and the Kubernetes Ingress route `/api/*`
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
node scripts/shot.mjs http://127.0.0.1:5173 /tmp/dashboard.png
```

## Status

| Area | State |
|---|---|
| Backend + REST API | Done |
| Database + Alembic | Done |
| Tests | Done (85 passing) |
| Frontend dashboard | Done |
| Docker / Compose (full stack) | Next |
| CI/CD + security scan | Next |
| Terraform / Kubernetes / Helm / monitoring | Next |