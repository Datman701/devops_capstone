# Submission Screenshots

Evidence for the graded modules. Regenerate with the commands in the last
section. All images are captured headlessly against the Docker Compose stack, so
they show the real containerised application rather than a dev server.

| # | File | Rubric item | What it shows |
|---|------|-------------|---------------|
| 01 | `01-dashboard.png` | M1, M4, M10 | Dashboard with KPI cards, upcoming schedule, activity feed and doctor load |
| 02 | `02-appointments.png` | M1 | Appointment list with the filter bar and **Apply filter** button |
| 03 | `03-appointments-filtered.png` | M1 | Same page after clicking Apply filter, filtered to `scheduled` |
| 04 | `04-doctors.png` | M1 | Doctor directory |
| 05 | `05-patients.png` | M1 | Patient directory |
| 06 | `06-booking-modal.png` | M1 | Booking modal with the availability picker, proving the browser reaches the API |
| 07 | `07-dashboard-mobile.png` | M1 (responsive UI) | Dashboard at 414 px — sidebar collapses, cards stack |
| 08 | `08-appointments-mobile.png` | M1 (responsive UI) | Appointments at 414 px |
| 09 | `09-pytest-passing.png` | **M2** | `pytest -v` — 85 passed |
| 10 | `10-docker-compose.png` | **M4** | `docker compose up --build` with all three services healthy, plus `/health` |
| 11 | `11-non-root-users.png` | **M4** | `docker exec … id` — backend `uid=1001(app)`, frontend `uid=101(nginx)` |
| 12 | `12-trivy-clean.png` | **M6** | Trivy reporting 0 HIGH / 0 CRITICAL for both images |
| 13 | `13-git-history.png` | **M3** | `git log` — 28 commits with descriptive messages |
| 14 | `14-github-actions-green.png` | **M5** | Successful pipeline run, all three jobs green |
| 15 | `15-ghcr-packages.png` | **M5** | GHCR package list showing `backend` and `frontend` |
| 16 | `16-ghcr-backend-tags.png` | **M5** | Package page showing SHA-based tags (short and full) |

## Still to capture

These depend on infrastructure that is not built yet, and will be added as the
remaining modules land.

| Rubric item | Expected file |
|-------------|---------------|
| M7 | `17-terraform-plan.png`, `18-aws-vpc-eks.png`, `19-terraform-destroy.png` — **blocked on AWS credentials** |
| M8 | `20-kubectl-pods.png`, `21-kubectl-svc.png`, `22-helm-list.png`, `23-app-via-ingress.png` |
| M9 | `24-metrics-endpoint.png`, `25-prometheus-targets.png`, `26-grafana-dashboard.png` |

## Regenerating

```bash
# Application screenshots (01-08) — stack must be running on :3000
docker compose up -d --build
node scripts/screenshots.mjs

# Terminal-style evidence (09-13)
cd backend && pytest -v > /tmp/pytest.txt && cd ..
node scripts/render-terminal.mjs /tmp/pytest.txt \
  docs/screenshots/09-pytest-passing.png "pytest -v"

docker compose up --build -d > /tmp/docker.txt
node scripts/render-terminal.mjs /tmp/docker.txt \
  docs/screenshots/10-docker-compose.png "docker compose up --build"

trivy image --severity HIGH,CRITICAL --ignore-untracked \
  clinicdesk-backend:local > /tmp/trivy.txt
node scripts/render-terminal.mjs /tmp/trivy.txt \
  docs/screenshots/12-trivy-clean.png "Trivy security scan"

git log --oneline --graph --decorate > /tmp/gitlog.txt
node scripts/render-terminal.mjs /tmp/gitlog.txt \
  docs/screenshots/13-git-history.png "commit history"
```

`render-terminal.mjs` takes a plain text file and renders it in a terminal
window, so any command output can be turned into a submittable image.

## Notes

- Screenshot 01 caught a real bug. The dashboard was rendering completely blank
  because a `BusyDoctors` component had been removed by mistake; React threw
  during render and the root element stayed empty. The browser console confirmed
  it was an application error rather than a capture problem.
- Screenshots are regenerated after every UI change, so they always reflect the
  current commit.