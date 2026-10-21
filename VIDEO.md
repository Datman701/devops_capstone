# ClinicDesk — M10 Video Walkthrough Script

**Target length: 4:00–4:30.** Record it in segments and cut the waits — the
pipeline takes ~4 minutes and ArgoCD takes ~1–2 minutes, neither of which belongs
in the final cut.

The rubric requires a live demo. No video means zero for M10, regardless of the
rest of the submission.

> **Golden rule:** do not read the slides. Say what you built, then prove it on
> screen.

---

## One-page cheat sheet

| # | Time | Segment | Action |
|---|------|---------|--------|
| 1 | 0:00–0:15 | Cold open | Slide 1 |
| 2 | 0:15–0:35 | PPT | Slides 3 and 4 |
| 3 | 0:35–0:50 | Codebase | Repo root + `frontend/src/App.jsx` |
| 4 | 0:50–1:10 | Live app | `http://localhost:18080` |
| 5 | 1:10–1:30 | Push | `./scripts/video-demo.sh change "..."` |
| 6 | 1:30–1:55 | CI/CD | GitHub Actions run |
| 7 | 1:55–2:20 | Terraform | `terraform validate` + screenshots |
| 8 | 2:20–2:50 | GitOps | `./scripts/video-demo.sh deploy` |
| 9 | 2:50–3:05 | Payoff | Reload the app |
| 10 | 3:05–3:25 | Kubernetes | `./scripts/video-demo.sh status` |
| 11 | 3:25–3:45 | Prometheus | `http://localhost:19090/targets` |
| 12 | 3:45–4:10 | Grafana | Dashboard + traffic loop |
| 13 | 4:10–4:25 | Close | Slide 12 |

---

## Before you record

### 1. Pre-flight

```bash
cd ~/Projects/devops_capstone/clinic-desk
./scripts/video-demo.sh preflight
```

You should see:

```text
✓ 5/5 pods Ready
✓ Synced/Healthy
Seeded 5 doctors, 8 patients, 115 appointments.
✓ app 200
✓ API health ok
✓ Prometheus healthy
✓ Grafana healthy
Repo HEAD:  cb7b4d3
Deployed:   29d8734
```

If a port-forward is dead, preflight restarts it. If it still fails, run
`./scripts/video-demo.sh stop` and then `preflight` again.

### 2. Tabs, in this order

1. `clinic-desk-deck.pdf` — full-screen PDF viewer
2. `http://localhost:18080` — the app
3. GitHub → Actions → the `CI/CD` workflow
4. GitHub → Packages → `backend` / `frontend`
5. `http://localhost:18081` — ArgoCD (`admin` / `Dx5C-KdMpGi829BV`)
6. `http://localhost:19090/targets` — Prometheus
7. `http://localhost:13000` — Grafana (`admin` / `clinicdesk`)

### 3. Capture settings

- OBS, 1920×1080, 30 fps, microphone checked.
- Terminal font at least 18 pt; clear scrollback.
- Notifications off (Do Not Disturb).
- One display only; hide personal tabs.
- Record each segment separately. You will assemble them in kdenlive.

---

## Segment-by-segment script

### 1. Cold open — 0:00–0:15

**Screen:** slide 1, full-screen.

**Say:**

> "Hi, I'm **[your name]**. This is **ClinicDesk** — a clinic appointment app
> built with FastAPI, React and PostgreSQL. The app itself is deliberately
> small; the real deliverable is everything around it: tests, containers, a
> security-gated pipeline, Kubernetes, GitOps and monitoring."

---

### 2. PPT — 0:15–0:35

**Screen:** slide 3 (architecture), then slide 4 (stack).

**Say:**

> "Every commit follows this path: GitHub Actions runs the tests and a Trivy
> scan, publishes SHA-tagged images to GHCR, ArgoCD syncs the Helm chart, and
> the app runs on Kubernetes with Prometheus and Grafana watching it."

Do not walk through the remaining slides — the live demo covers them.

---

### 3. Codebase — 0:35–0:50

**Screen:** editor with the repo root visible, then `frontend/src/App.jsx`.

**Say:**

> "Everything lives in one repository — backend, frontend, workflows, Helm
> chart, Terraform and monitoring. I'm changing one line in the dashboard
> subtitle so the deployment is visibly different."

Keep this to 15 seconds. The folder tour is not worth screen time.

---

### 4. Live app — 0:50–1:10

**Screen:** `http://localhost:18080`, Dashboard.

**Say:**

> "This is running in Kubernetes, behind an ingress, not on my laptop. The badge
> next to the title is the commit SHA the image was built from — right now
> `29d8734`. The rows are live from PostgreSQL."

**Do:** click **Appointments**, show the list, then go back to the Dashboard.
Optionally book one appointment — 10 seconds, and it proves the write path.

---

### 5. Make the change and push — 1:10–1:30

**Terminal:**

```bash
./scripts/video-demo.sh change "Appointments, deployed by the pipeline"
```

The script prints the diff, commits, pushes to `main`, and prints the Actions
run URL.

**Say:**

> "One line changed, committed, pushed to main. That push is what starts the
> pipeline."

---

### 6. CI/CD — 1:30–1:55

**Screen:** the GitHub Actions run.

**Say:**

> "Three gated jobs. The backend job runs **85 pytest tests** — if one fails,
> nothing is built. The frontend job builds the production bundle. Then both
> images are built and scanned by **Trivy**; a HIGH or CRITICAL finding fails
> the build **before** anything is pushed. Only then are the images published to
> GHCR, tagged with this commit's SHA — never `latest`."

**Do:**

- Open the **Backend tests** job and show `85 passed`.
- Open the Trivy step and show `0 HIGH / CRITICAL`.
- Optionally show the new SHA tag on the GHCR package page.

**Editing:** cut the 4-minute wait, or speed-ramp it 8×.

---

### 7. Terraform — 1:55–2:20

**Terminal:**

```bash
terraform -chdir=terraform validate
```

It succeeds offline. Then show the two screenshots full-screen:

1. `docs/screenshots/17-terraform-plan.png`
2. `docs/screenshots/18-aws-eks-cluster.png`

**Say:**

> "The cluster this deploys onto is defined in Terraform: a VPC with two public
> and two private subnets, an internet gateway, and an EKS cluster with a
> managed two-node group. This is the plan — **27 resources**. I applied it
> against a real AWS account and captured the console: the cluster came up
> **Active on Kubernetes 1.36**, with a node group of desired size 2. I then ran
> `terraform destroy` so nothing kept billing. **My AWS credits are exhausted,
> so I can't re-run apply live today** — but the full configuration is in
> `terraform/` and validates cleanly."

This is the honest workaround. Say it plainly; don't rush it.

---

### 8. GitOps deploy — 2:20–2:50

**Terminal:**

```bash
./scripts/video-demo.sh deploy
```

The script:

1. verifies CI is green for the new commit,
2. verifies both images exist in GHCR,
3. pins the new SHA in `argocd/application.yaml`,
4. commits and pushes that pin,
5. applies the Application and waits for ArgoCD,
6. waits for both rollouts and prints the new image tags.

**Say:**

> "CI publishes an image; it doesn't touch the cluster. Deployment is GitOps. I
> pin the new SHA in the ArgoCD Application, commit that, and apply it. ArgoCD
> renders the Helm chart from Git and rolls the pods onto the new image."

**Screen:** let the diff, the `kubectl apply`, the ArgoCD wait and the rollout
status play. Then open the ArgoCD UI:

```bash
kubectl -n argocd get application clinicdesk
```

> "Synced and Healthy."

**Editing:** speed-ramp the ArgoCD wait if it is longer than ~10 seconds.

---

### 9. The payoff — 2:50–3:05

**Screen:** reload `http://localhost:18080`.

**Say:**

> "Same URL. The subtitle changed, and the badge now shows the new commit. That
> is the pipeline end to end: commit → test → scan → image → GitOps → running
> pod."

This is the money shot. Hold on the new badge for at least three seconds.

---

### 10. Kubernetes — 3:05–3:25

**Terminal:**

```bash
./scripts/video-demo.sh status
```

**Say:**

> "Five pods running: two backend, two frontend, one PostgreSQL. All services
> are ClusterIP, and the ingress routes `/api` to the backend and everything
> else to the frontend."

Point at the pods, services and ingress lines as you say it.

> **Do not run `helm list -n clinicdesk`.** The app is ArgoCD-managed, so the
> release list is empty. The Helm evidence already exists in `screenshots.md`.

---

### 11. Prometheus — 3:25–3:45

**Screen:** `http://localhost:19090/targets`.

**Do:** type `clinicdesk-api` in the filter box.

**Say:**

> "Prometheus scrapes the API through its own metrics service. The
> `clinicdesk-api` target is **UP**, scraping every 15 seconds."

---

### 12. Grafana — 3:45–4:10

**Screen:** `http://localhost:13000` → dashboard **ClinicDesk API**.

**Say:**

> "The provisioned dashboard reads the same Prometheus instance: target health,
> request rate, p95 latency and the 5xx ratio."

**Do:** in a second terminal, generate traffic:

```bash
for i in $(seq 1 100); do
  curl -s -o /dev/null http://localhost:18080/api/appointments
done
```

Then point at the moving panels.

**Say:**

> "Those requests just moved the panels — this is live, not a screenshot."

---

### 13. Close — 4:10–4:25

**Screen:** slide 12.

**Say:**

> "Eighty-five tests, zero HIGH or CRITICAL vulnerabilities, five pods running,
> twenty-seven Terraform resources. Everything is reproducible from the commit.
> The repository link is below."

Stop recording.

---

## Editing

- Assemble the segments in **kdenlive**.
- Cut the CI wait and the ArgoCD wait. If you want to keep the sense of time,
  speed-ramp those clips 8× rather than deleting them.
- Add lower-thirds at each segment: `M5 CI/CD`, `M7 Terraform`, `GitOps`,
  `M8 Kubernetes`, `M9 Observability`. It lets the grader map footage to the
  rubric instantly.
- Burn in nothing else — no music, no long intro.
- Export **H.264 MP4, 1080p, 30 fps**.
- Watch the final cut once at 1× and check that every claim is visible on screen.

---

## Upload and submission

1. Upload to YouTube (**Unlisted**) or Google Drive (view access).
2. Put the link at the top of `README.md` and in the submission form.
3. Keep the cluster running until the evaluation; if the machine restarts, run
   `./scripts/video-demo.sh preflight` and the demo state comes back.

---

## Re-takes

`change` replaces whatever subtitle is currently in `App.jsx`, so you can run it
again with a different line:

```bash
./scripts/video-demo.sh change "Appointments, live from the pipeline (take 2)"
```

Each take creates a new commit and a new pipeline run. If only a browser clip
failed, re-record just that clip — don't redo the push.

---

## If something breaks

| Symptom | Fix |
|---|---|
| A port-forward died | `./scripts/video-demo.sh preflight` |
| Frontend pod crashlooping after a cluster restart | `kubectl -n clinicdesk rollout restart deploy/clinicdesk-frontend` |
| CI is red | Open the failing job. Do not deploy. Re-run failed jobs after fixing. |
| `deploy` says CI is not green | Wait for the run, then re-run `./scripts/video-demo.sh deploy` |
| `deploy` says the image is missing | The push step has not finished; wait and retry |
| ArgoCD stays `OutOfSync` | `kubectl -n argocd describe application clinicdesk` and check the image pull events |
| ArgoCD is slow | Keep recording; cut the wait. Last resort: pause auto-sync and use `./scripts/demo-deploy.sh <sha>` |

---

## What not to show

- `helm list -n clinicdesk` — empty, because ArgoCD owns the deployment.
- The **second** pipeline run started by the GitOps commit — expected, not part
  of the story.
- A raw `git log` after the GitOps commit. HEAD is one commit ahead of the
  deployed image; the badge is the **image** commit. If it comes up, say:
  *"the badge is the commit the image was built from; the GitOps commit only
  pins that SHA."*
- A live `terraform plan` or `apply` — the credentials are expired.
