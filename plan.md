# 📋 DevOps Capstone Execution Plan

## Module Status
- M1 (Application): ✅ COMPLETE
- M2 (Testing): ✅ COMPLETE
- M3 (Git/GitHub): ⬜ NOT STARTED
- M4 (Docker): ⬜ NOT STARTED
- M5 (CI/CD): ⬜ NOT STARTED
- M6 (DevSecOps): ⬜ NOT STARTED
- M7 (Terraform): ⬜ NOT STARTED
- M8 (Kubernetes + Helm): ⬜ NOT STARTED
- M9 (Observability): ⬜ NOT STARTED
- M10 (Presentation): ⬜ NOT STARTED

## M4: Docker (10 points)
- [ ] Create `backend/Dockerfile` (multi-stage, non-root, Python 3.12)
- [ ] Create `frontend/Dockerfile` (Node build → Nginx runtime, non-root)
- [ ] Update `docker-compose.yml` to include frontend + backend + postgres
- [ ] Test: `docker compose up --build` - all 3 services running
- [ ] Verify images run as non-root

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

## M8: Kubernetes + Helm (15 points)
- [ ] `k8s/namespace.yaml`
- [ ] `helm/clinicdesk/` chart (Chart.yaml, values.yaml, templates)
- [ ] 2+ replicas for backend + frontend
- [ ] ClusterIP Services
- [ ] Ingress: `/` → frontend, `/api` → backend
- [ ] Test: helm upgrade --install, pods running

## M9: Observability (10 points)
- [ ] Backend `/metrics` endpoint
- [ ] `monitoring/` with Prometheus + Grafana values
- [ ] Verify Prometheus scraping
- [ ] Grafana dashboard showing metrics

## M10: Presentation (5 points)
- [ ] Update README with DevOps instructions
- [ ] Prepare live demo
