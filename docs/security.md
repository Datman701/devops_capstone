# M6 — DevSecOps: Trivy Security Scanning

## What Trivy scans

Trivy runs inside the CI pipeline as a **gate** on both container images before
they are published to GitHub Container Registry. It performs two separate scans
against each image:

1. **OS packages** (`--scanners vuln` on the base image's Debian/Alpine
   package database) — finds CVEs in the Linux distribution packages that the
   `python:3.12-slim-bookworm` and `nginx:*-alpine` base images bring in.
2. **Application dependencies** — reads the installed Python
   `dist-info/METADATA` files in `/opt/venv` and reports CVEs in the exact
   versions pinned in `backend/requirements.txt`, including packages that are
   only vendored inside another package.

The scan is configured with:

```yaml
severity: HIGH,CRITICAL
ignore-unfixed: true
exit-code: '1'
```

`exit-code: '1'` is what makes it a gate: Trivy exits non-zero, the step fails,
and the `Push ... to GHCR` steps are skipped because they run after it in the
same job. A vulnerable image therefore cannot reach the registry.

`ignore-unfixed: true` means only CVEs **with an available patch** block the
build. Vulnerabilities with no fix yet are still listed in the scan table, but
they cannot be remediated by this project and would otherwise block every
future build with no action available.

---

## Findings from the first scan

The first pipeline run failed exactly as designed. Trivy reported
**7 HIGH, 0 CRITICAL** vulnerabilities in the backend image and blocked the
publish:

```
Total: 7 (HIGH: 7, CRITICAL: 0)
```

| Library | Vulnerability | Installed | Fixed | Title |
|---|---|---|---|---|
| msgpack | GHSA-6v7p-g79w-8964 | 1.1.2 | 1.2.1 | Out-of-bounds read / crash on unpacker reuse |
| setuptools | CVE-2025-47273 | 70.3.0 | 78.1.1 | Path traversal in `PackageIndex` |
| starlette | CVE-2025-62727 | 0.41.3 | 0.49.1 | DoS via Range header merging |
| starlette | CVE-2026-48818 | — | 1.1.0 | SSRF and NTLM credential theft via UNC |
| starlette | CVE-2026-54283 | — | 1.3.1 | `request.form()` limits silently ignored |
| urllib3 | CVE-2026-97687 | 2.7.0 | 2.8.0 | Traffic interception via HTTPS proxy TLS override |
| urllib3 | CVE-2026-97689 | — | 2.8.0 | Denial of service via unbounded memory in chunk parser |

The frontend image was worse: **45 findings (43 HIGH, 2 CRITICAL)**, all OS
packages in the stale `nginx:1.27-alpine` base image (Alpine 3.21) —
`libssl3`, `libcrypto3`, `libexpat`, `libpng`, `libxml2`, `musl`.

---

## CVE explained: CVE-2025-47273 (setuptools path traversal)

This is a good example of a finding that looks alarming in a report but is not
actually reachable in this project — and fixing it properly meant changing the
image rather than bumping a version number.

**The flaw.** `setuptools`' `PackageIndex` class resolves package download URLs
by appending the requested filename to a base URL. When the filename is derived
from user-controlled input and not sanitised, an attacker can supply a value
like `../../../../etc/passwd`, causing setuptools to read or write files outside
the intended directory. In a build system or CI runner that executes untrusted
package names, this turns into arbitrary file disclosure or overwrite.

**Why it mattered here.** `backend/Dockerfile` builds a virtualenv with
`python -m venv`, which seeds `pip`, `setuptools` and `wheel` from whatever the
base image ships — `70.3.0` at the time. So the vulnerable `PackageIndex` was
present in the runtime image.

**The fix, in two parts.** First, the builder stage now upgrades the build
tooling before installing anything:

```dockerfile
RUN pip install --upgrade pip setuptools wheel
```

Second — and this is the part that actually cleared the finding — the runtime
stage **removes pip entirely**:

```dockerfile
RUN /opt/venv/bin/python -m pip uninstall -y pip setuptools wheel && rm -rf ...
```

This was necessary because a plain `pip install --upgrade setuptools` in the
builder was not enough. A rescan still reported the same three HIGH findings
(`msgpack 1.1.2`, `setuptools 70.3.0`, `urllib3 2.7.0`) even though
`pip list` inside the image showed `setuptools 84.0.0` and `urllib3 2.8.0`. The
cause was that **pip vendors its own copies** of these libraries under
`pip/_vendor/`:

```
/opt/venv/lib/python3.12/site-packages/pip/_vendor/vendor.txt
  msgpack==1.1.2
  setuptools==70.3.0
```

Those vendored copies are what Trivy was reading, and they are the versions
bundled inside pip itself — upgrading setuptools never touches them. The
application never imports them; only pip does, at install time. Since nothing is
compiled at run time, deleting pip from the runtime image removes both the
findings and roughly 12 MB, and is standard practice for production images.

---

## Other remediations

| Finding | Fix |
|---|---|
| starlette CVEs (3) | Upgraded FastAPI 0.115.6 → 0.143.0, which pulls starlette 1.7.0 |
| urllib3 CVEs (2) | Pinned `urllib3==2.8.0` explicitly in `requirements.txt` |
| msgpack GHSA-6v7p-g79w-8964 | Removed — dropped entirely by upgrading Alembic 1.14.0 → 1.20.0, then eliminated with pip |
| setuptools CVE-2025-47273 | Removed with pip (see above) |
| frontend 45 Alpine CVEs | Base image `nginx:1.27-alpine` (Alpine 3.21) → `nginx:1.30.5-alpine` (Alpine 3.24), pinned to an exact patch tag |
| 3 remaining Alpine CVEs (libexpat, pcre2, tiff) | `RUN apk upgrade --no-cache` in the runtime stage |

### One dependency conflict worth recording

Upgrading FastAPI to 0.143.0 initially broke the entire test suite — 84 of 85
tests failed with:

```
AttributeError: '_IncludedRouter' object has no attribute 'path'
  at prometheus_fastapi_instrumentator/routing.py:55
```

FastAPI 0.14x introduced an internal `_IncludedRouter` type, and
`prometheus-fastapi-instrumentator` 7.0.0 assumed every route object had a
`.path` attribute. The fix was to move to
`prometheus-fastapi-instrumentator==8.1.0`, which supports the new router
structure. A version constraint is recorded in `requirements.txt` so this is
not silently reintroduced.

This is the practical argument for a scanning gate: the dependency upgrades
required to clear the CVEs surfaced an unrelated incompatibility that would
otherwise have been discovered in production.

---

## Final state

Both images now report **0 HIGH and 0 CRITICAL** findings:

```console
$ trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 clinicdesk-backend:local
Total: 0

$ trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 clinicdesk-frontend:local
Total: 0
```

Reproduce locally against the built images:

```bash
docker compose build
trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed \
  --exit-code 1 clinicdesk-backend:local
trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed \
  --exit-code 1 clinicdesk-frontend:local
```

Scan results for each pipeline run are visible in the Actions job log under
`Build, scan and publish images`.