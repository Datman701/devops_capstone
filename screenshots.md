# Submission Screenshots

Every graded artifact in one place, each with what it demonstrates and which
rubric item it satisfies.

All images are generated headlessly, so they always reflect the current commit.
Regenerate with `./scripts/screenshots.sh` (see [Regenerating](#regenerating)).

---

## M1 — Application (10 points)

The application running, served by the containerised stack. Frontend, backend
and database all in Docker, reached through nginx on port 3000.

### 1. Dashboard

![Dashboard showing KPI cards, upcoming schedule, recent activity and a doctor load ranking](docs/screenshots/01-dashboard.png)

The operations overview: appointment totals with a status breakdown, today's
count, the next seven days, the cancellation rate and the patient count. Below
it, the upcoming schedule with inline Advance/Cancel actions, a recent activity
feed, and a ranked doctor-load panel.

### 2. Appointments with the filter bar

![Appointments list with status, doctor, date range and upcoming filters above an Apply filter button](docs/screenshots/02-appointments.png)

The full appointment list. Note the **Apply filter** button: changing a control
only edits a draft, and the query runs when Apply is pressed — so a stray click
cannot fire a request.

### 3. Appointments after applying a filter

![The same page filtered to scheduled appointments after pressing Apply filter](docs/screenshots/03-appointments-filtered.png)

Evidence that the Apply interaction works end to end: the status dropdown was
changed and Apply pressed, and the table reloaded from the filtered query.

### 4. Doctor directory

![Doctor directory listing names, specialties, consultation fees and appointment counts](docs/screenshots/04-doctors.png)

The practitioner roster, with inline create and delete.

### 5. Patient directory

![Patient directory listing names, phone numbers and email addresses](docs/screenshots/05-patients.png)

Registered patients, with inline create and delete.

### 6. Booking modal

![Booking modal with doctor and patient selectors, a date picker and an availability grid](docs/screenshots/06-booking-modal.png)

The booking flow. Picking a doctor and date populates the availability grid from
the API, so this screenshot also demonstrates that the browser reaches the
backend successfully.

### 7. Dashboard on mobile

![Dashboard at 414 pixels wide, with the sidebar collapsed into a hamburger and the cards stacked](docs/screenshots/07-dashboard-mobile.png)

Responsive layout at phone width — the sidebar collapses and the KPI cards
reflow into a single column.

### 8. Appointments on mobile

![Appointments list at 414 pixels wide](docs/screenshots/08-appointments-mobile.png)

The same page on a narrow viewport.

---

## M2 — Testing (10 points)

### 9. Test suite passing

![pytest verbose output listing 85 passing tests across CRUD, conflicts, filters, stats and validation](docs/screenshots/09-pytest-passing.png)

`pytest -v` against a throwaway `clinic_test` database: **85 passed**. Covers
appointment CRUD, slot-conflict handling, filters, directory endpoints, stats,
health probes and input validation. Each test runs inside a transaction that is
rolled back, so the suite cannot leak rows into development data.

---

## M3 — Git and GitHub (5 points)

### 10. Commit history

![git log showing the commit history in a labelled graph](docs/screenshots/13-git-history.png)

Conventional, descriptive commits (`feat(api):`, `fix(ci):`, `build(docker):`)
split into logical slices, so the history reads as a narrative rather than a
series of "update" messages.

---

## M4 — Docker (10 points)

### 11. The stack running

![docker compose up --build output followed by docker compose ps showing three healthy containers](docs/screenshots/10-docker-compose.png)

`docker compose up --build` builds both images and starts all three services,
each reporting **healthy**. The final line is the API's own `/health` response.

### 12. Non-root containers

![docker exec id showing uid=1001(app) for the backend and uid=101(nginx) for the frontend](docs/screenshots/11-non-root-users.png)

Neither application image runs as root: the backend as `uid=1001(app)`, the
frontend as the stock `uid=101(nginx)`.

---

## M5 — CI/CD (15 points)

### 13. Green pipeline run

![GitHub Actions showing a successful run with the backend tests, frontend build and image publish jobs all green](docs/screenshots/14-github-actions-green.png)

Three gated jobs: tests and the frontend build must pass before any image is
built, scanned or published.

### 14. GHCR packages

![The GitHub container registry listing the backend and frontend packages](docs/screenshots/15-ghcr-packages.png)

Both images are published to GitHub Container Registry.

### 15. SHA-based image tags

![The backend package page listing tagged versions with short and full commit SHA tags](docs/screenshots/16-ghcr-backend-tags.png)

Each image is tagged with the full and short commit SHA — never `latest` — so a
running deployment can always be traced back to exactly one commit.

---

## M6 — DevSecOps (5 points)

### 16. Trivy security scan

![Trivy output showing zero vulnerabilities for the Debian and Alpine targets](docs/screenshots/12-trivy-clean.png)

Both images report **0 HIGH and 0 CRITICAL**. Trivy scans the OS package
database *and* the installed Python packages, and runs as a gate: `exit-code: 1`
means a vulnerable image can never reach the registry. The findings this
remediated, and what each one meant, are written up in [docs/security.md](docs/security.md).

---

## M7 — Terraform (15 points)

### 17. Configuration validated and planned

![terraform validate succeeding followed by a plan showing 27 resources to be created](docs/screenshots/17-terraform-plan.png)

`terraform validate` passes, and the plan is non-empty and error-free: **27
resources**, including the two public subnets and the EKS cluster with its
managed worker node group the rubric requires.

> Captured with mock credentials and pinned availability zones, so the plan
> renders without contacting AWS. Run against a real account for the graded
> `terraform plan` screenshot — see [Remaining](#remaining) below.

---

## M8 — Kubernetes + Helm (15 points)

### 18. Cluster resources

![kubectl get pods, get svc and get ingress output, plus helm list showing the clinicdesk release deployed](docs/screenshots/20-kubectl-resources.png)

Five pods **Running** (two backend replicas, two frontend replicas, one
PostgreSQL), all Services **ClusterIP**, and the Helm release `deployed`.

### 19. Dashboard through the Ingress

![Dashboard served through the nginx Ingress, showing live seeded data](docs/screenshots/21-app-via-ingress-dashboard.png)

The application reached the way a user would: browser → Ingress → nginx →
backend. This is the same page as screenshot 1, but from the Kubernetes
deployment rather than Compose.

### 20. Appointments through the Ingress

![Appointments page served through the Ingress](docs/screenshots/22-app-via-ingress-appointments.png)

Proves `/api/*` routes to the backend while everything else falls through to
the SPA.

### 21. Booking modal through the Ingress

![Booking modal served through the Ingress](docs/screenshots/23-app-via-ingress-booking.png)

The full write path works inside the cluster.

---

## M9 — Observability (10 points)

### 22. Metrics endpoint

![Prometheus-formatted output from /metrics showing the http_requests_total counter and duration histogram](docs/screenshots/24-metrics-endpoint.png)

The backend exposes Prometheus-formatted text, including the
`http_requests_total` counter and the `http_request_duration_seconds` histogram
the dashboard queries.

### 23. Prometheus targets

![Prometheus target health page showing the clinicdesk-api target as UP](docs/screenshots/25-prometheus-targets.png)

Prometheus is installed in the cluster and scraping the API — the
`clinicdesk-api` target reports **UP**.

### 24. Grafana dashboard

![Grafana dashboard with target up, requests per second, p95 latency, error rate, and three time series charts](docs/screenshots/26-grafana-dashboard.png)

Nine provisioned panels, all live: target health (**UP**), request rate
(1.49 req/s), p95 latency (4.750 ms), 5xx error ratio (0.00 %), cumulative
requests, request rate by endpoint, response status codes, latency percentiles
and average latency by endpoint.

---

## Remaining

| Rubric item | Screenshot | Status |
|-------------|-----------|--------|
| M7 | AWS Console showing the VPC and EKS cluster | Needs a real `terraform apply` |
| M7 | `terraform destroy` completion | Run after the apply, so the cluster stops billing |
| M7 | `terraform plan` against real credentials | Covered in principle by screenshot 17 |

---

## Regenerating

```bash
./scripts/screenshots.sh
```

Individual steps, if you only need one:

```bash
# Application (M1) — stack must be running on :3000
docker compose up -d --build
node scripts/screenshots.mjs

# Terminal-style evidence (M2-M7)
node scripts/render-terminal.mjs /tmp/out.txt out.png "title"

# Kubernetes (M8)
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 18080:80 &
node scripts/screenshots.mjs http://127.0.0.1:18080 /tmp/k8s-shots

# Monitoring (M9)
kubectl port-forward -n monitoring svc/grafana 13000:80 &
kubectl port-forward -n monitoring svc/prometheus-server 19090:80 &
node scripts/screenshot-grafana.mjs http://127.0.0.1:13000 out.png
```

`render-terminal.mjs` turns any captured command output into a terminal-styled
PNG, which is how the pytest, Docker, Trivy and Terraform evidence is produced.

---

## Notes

- Screenshot 1 caught a real bug. The dashboard was rendering completely blank
  because a `BusyDoctors` component had been removed by mistake; React threw
  during render and the root element stayed empty. The browser console confirmed
  it was an application fault rather than a capture problem.
- `screenshot-grafana.mjs` asserts that panels actually rendered before writing
  the image, so a broken datasource can never produce a pretty but empty
  screenshot.