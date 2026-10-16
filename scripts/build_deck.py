#!/usr/bin/env python3
"""Build the ClinicDesk DevOps capstone slide deck (clinic-desk-deck.pptx)."""

Native shapes + text only (editable), explicit inch coordinates, 16:9.
"""
from __future__ import annotations

import os

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

REPO = os.environ.get("REPO", "github.com/Datman701/devops_capstone")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "docs", "screenshots")
OUT = os.path.join(ROOT, "clinic-desk-deck.pptx")

W, H = 13.333, 7.5
ML, MR = 0.6, 0.6
FONT = "Calibri"

# palette
INK = "0F172A"
BODY = "334155"
MUTED = "64748B"
ACCENT = "2563EB"
ACCENT_D = "1D4ED8"
SKY = "0EA5E9"
SKY_L = "38BDF8"
PANEL = "F1F5F9"
PANEL_B = "E2E8F0"
GREEN = "16A34A"
WHITE = "FFFFFF"
DARK = "0F172A"
DARK_PANEL = "1E293B"
DARK_BORDER = "334155"
DARK_MUTED = "94A3B8"
DARK_TEXT = "CBD5E1"


# ---------------------------------------------------------------- helpers
def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    return prs


def blank(prs, dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(DARK if dark else WHITE)
    return slide


def tb(slide, x, y, w, h, lines, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = ln.get("align", align)
        if "before" in ln:
            p.space_before = Pt(ln["before"])
        if "after" in ln:
            p.space_after = Pt(ln["after"])
        if "line" in ln:
            p.line_spacing = ln["line"]
        run = p.add_run()
        run.text = ln["text"]
        f = run.font
        f.name = ln.get("font", FONT)
        f.size = Pt(ln.get("size", 16))
        f.bold = ln.get("bold", False)
        f.italic = ln.get("italic", False)
        f.color.rgb = RGBColor.from_string(ln.get("color", BODY))
        if ln.get("spacing"):
            f._rPr.set("spc", str(int(ln["spacing"] * 100)))
    return box


def rect(slide, x, y, w, h, fill=None, line=None, lw=0.75,
         shape=MSO_SHAPE.RECTANGLE, radius=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = RGBColor.from_string(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = RGBColor.from_string(line)
        s.line.width = Pt(lw)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def pic_fit(slide, name, x, y, w, h, border=True, alt=None):
    path = os.path.join(SHOTS, name)
    iw, ih = Image.open(path).size
    ar, bar = iw / ih, w / h
    dw, dh = (w, w / ar) if ar >= bar else (h * ar, h)
    px, py = x + (w - dw) / 2, y + (h - dh) / 2
    if border:
        rect(slide, px, py, dw, dh, fill=None, line=PANEL_B, lw=1.0)
    pic = slide.shapes.add_picture(path, Inches(px), Inches(py), Inches(dw), Inches(dh))
    if alt:
        pic._element._nvXxPr.cNvPr.set("descr", alt)
    return pic


def header(slide, eyebrow, title, dark=False):
    tb(slide, ML, 0.36, 9.0, 0.3,
       [{"text": eyebrow, "size": 12, "bold": True, "color": SKY_L if dark else ACCENT,
         "spacing": 1.5}])
    tb(slide, ML, 0.64, 12.1, 0.78,
       [{"text": title, "size": 27, "bold": True, "color": WHITE if dark else INK}])
    rect(slide, ML + 0.02, 1.40, 0.95, 0.06, fill=ACCENT)


def footer(slide, n):
    rect(slide, ML, 7.06, W - ML - MR, 0.012, fill=PANEL_B)
    tb(slide, ML, 7.10, 8.0, 0.3, [{"text": REPO, "size": 9.5, "color": MUTED}])
    tb(slide, W - MR - 1.0, 7.10, 1.0, 0.3,
       [{"text": f"{n:02d}", "size": 9.5, "color": MUTED, "align": PP_ALIGN.RIGHT}])


def bullets(slide, x, y, w, items, dark=False):
    lines = []
    for i, (head, _body) in enumerate(items):
        lines.append({"text": head, "size": 15.5, "bold": True,
                      "color": WHITE if dark else INK,
                      "before": 0 if i == 0 else 13})
        if _body:
            lines.append({"text": _body, "size": 13, "color": DARK_TEXT if dark else BODY,
                          "line": 1.12, "before": 3})
    tb(slide, x, y, w, 4.6, lines)


# ---------------------------------------------------------------- slides
def slide_title(prs):
    s = blank(prs, dark=True)
    rect(s, 0, 0, 0.30, H, fill=ACCENT)
    rect(s, 0.30, 0, 0.06, H, fill=SKY)
    rect(s, 9.55, 0, 3.78, H, fill="131C31")

    tb(s, 1.15, 1.42, 10.5, 0.4,
       [{"text": "DEVOPS  CAPSTONE  ·  END-TO-END  DELIVERY", "size": 13,
         "bold": True, "color": SKY_L, "spacing": 2.4}])
    tb(s, 1.10, 1.86, 11.0, 1.1,
       [{"text": "ClinicDesk", "size": 54, "bold": True, "color": WHITE}])
    tb(s, 1.15, 3.02, 10.2, 1.0,
       [{"text": "A clinic appointments app — built, tested, scanned,", "size": 20,
         "color": DARK_TEXT, "line": 1.25},
        {"text": "and deployed by pipeline, not by hand.", "size": 20,
         "color": DARK_TEXT, "line": 1.25}])
    tb(s, 1.15, 4.42, 11.0, 0.4,
       [{"text": "commit  →  test  →  scan  →  publish  →  GitOps  →  cluster  →  observe",
         "size": 14.5, "color": DARK_MUTED, "spacing": 0.4}])
    rect(s, 1.15, 5.30, 4.2, 0.02, fill=DARK_BORDER)
    tb(s, 1.15, 5.52, 11.0, 0.9,
       [{"text": REPO, "size": 15, "bold": True, "color": SKY_L},
        {"text": "Terraform  ·  Kubernetes  ·  Helm  ·  GitHub Actions  ·  ArgoCD  ·  Prometheus  ·  Grafana",
         "size": 11.5, "color": DARK_MUTED, "before": 5}])
    # decorative dots
    for i, c in enumerate([SKY, ACCENT, "1E40AF"]):
        rect(s, 11.95 + i * 0.42, 1.55, 0.26, 0.26, fill=c,
             shape=MSO_SHAPE.OVAL)


def slide_product(prs, n):
    s = blank(prs)
    header(s, "01 · THE PRODUCT", "One small app, one serious pipeline")
    tb(s, ML, 1.72, 6.2, 1.3,
       [{"text": "ClinicDesk manages doctors, patients, and appointment bookings. "
                 "It is deliberately small — the real deliverable is everything "
                 "around it: automated builds, security scans, infrastructure, "
                 "deployment, and observability.", "size": 14.5, "color": BODY,
         "line": 1.28}])
    rows = [
        ("Frontend", "React + Vite, served by nginx"),
        ("Backend", "FastAPI · Python 3.12 · REST API + /metrics"),
        ("Database", "PostgreSQL 16 with persistent storage"),
    ]
    y = 3.28
    for label, desc in rows:
        rect(s, ML, y, 6.2, 0.94, fill=PANEL, line=PANEL_B,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
        rect(s, ML, y, 0.08, 0.94, fill=ACCENT)
        tb(s, ML + 0.32, y + 0.14, 2.1, 0.66,
           [{"text": label, "size": 14.5, "bold": True, "color": INK}])
        tb(s, ML + 2.35, y + 0.17, 3.75, 0.62,
           [{"text": desc, "size": 12, "color": MUTED, "line": 1.05}])
        y += 1.06
    pic_fit(s, "01-dashboard.png", 7.15, 1.72, 5.55, 4.75,
            alt="ClinicDesk dashboard: KPI cards for appointments, patients and doctors")
    footer(s, n)


def slide_arch(prs, n):
    s = blank(prs)
    header(s, "02 · ARCHITECTURE", "Every step is automated")
    tb(s, ML, 1.66, 12.1, 0.35,
       [{"text": "A commit travels a fully automated path from developer to a measured, running container.",
         "size": 14, "color": BODY}])
    boxes = [
        ("Dev", "commit", False),
        ("GitHub", "repository", False),
        ("Actions", "test · scan · build", True),
        ("GHCR", "SHA-tagged image", False),
        ("ArgoCD", "GitOps sync", False),
        ("Kubernetes", "kind · EKS", False),
        ("Metrics", "Prometheus · Grafana", False),
    ]
    bw, bh, gap, y = 1.35, 1.3, 0.4, 2.38
    total = len(boxes) * bw + (len(boxes) - 1) * gap
    x = (W - total) / 2
    for i, (name, sub, hi) in enumerate(boxes):
        fill = ACCENT if hi else PANEL
        rect(s, x, y, bw, bh, fill=fill, line=None if hi else PANEL_B,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
        tb(s, x + 0.07, y + 0.30, bw - 0.14, 0.7,
           [{"text": name, "size": 12.5, "bold": True,
             "color": WHITE if hi else INK, "align": PP_ALIGN.CENTER},
            {"text": sub, "size": 9, "color": "DBEAFE" if hi else MUTED,
             "align": PP_ALIGN.CENTER, "line": 1.05, "before": 2}])
        if i < len(boxes) - 1:
            ax = x + bw + 0.03
            rect(s, ax, y + bh / 2 - 0.12, gap - 0.06, 0.24, fill=SKY,
                 shape=MSO_SHAPE.RIGHT_ARROW)
        x += bw + gap
    bullets(s, ML, 4.30, 12.1, [
        ("Gated by design", "Nothing reaches the cluster unless it passes tests and the security scan."),
        ("Reproducible", "The chart deploys the same SHA-tagged images that CI published."),
    ])
    footer(s, n)


def slide_stack(prs, n):
    s = blank(prs)
    header(s, "03 · STACK", "Tools chosen for automation, not novelty")
    cards = [
        ("APP", "FastAPI · React", "PostgreSQL 16"),
        ("CONTAINERS", "Docker", "multi-stage builds"),
        ("CI / CD", "GitHub Actions", "gated jobs"),
        ("REGISTRY", "GHCR", "commit-SHA tags"),
        ("INFRA", "Terraform", "AWS VPC + EKS"),
        ("RUNTIME", "Kubernetes", "+ Helm chart"),
        ("GITOPS", "ArgoCD", "declarative sync"),
        ("METRICS", "Prometheus", "+ Grafana"),
    ]
    cw, ch, gx, gy = 2.85, 1.72, 0.22, 0.30
    x0 = (W - (4 * cw + 3 * gx)) / 2
    for i, (tag, name, sub) in enumerate(cards):
        r, c = divmod(i, 4)
        x = x0 + c * (cw + gx)
        y = 2.15 + r * (ch + gy)
        rect(s, x, y, cw, ch, fill=PANEL, line=PANEL_B,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.10)
        rect(s, x, y, cw, 0.30, fill=ACCENT,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.10)
        rect(s, x, y + 0.13, cw, 0.17, fill=ACCENT)
        tb(s, x, y + 0.045, cw, 0.26,
           [{"text": tag, "size": 10.5, "bold": True, "color": WHITE,
             "align": PP_ALIGN.CENTER, "spacing": 1.2}])
        tb(s, x + 0.2, y + 0.46, cw - 0.4, 0.6,
           [{"text": name, "size": 15, "bold": True, "color": INK,
             "align": PP_ALIGN.CENTER}])
        tb(s, x + 0.2, y + 1.02, cw - 0.4, 0.5,
           [{"text": sub, "size": 11.5, "color": MUTED, "align": PP_ALIGN.CENTER}])
    footer(s, n)


def slide_split(prs, n, eyebrow, title, intro, items, img, alt):
    s = blank(prs)
    header(s, eyebrow, title)
    if intro:
        tb(s, ML, 1.68, 6.05, 0.6, [{"text": intro, "size": 13.5, "color": MUTED,
                                     "line": 1.2}])
        iy = 2.42
    else:
        iy = 1.95
    bullets(s, ML, iy, 6.05, items)
    pic_fit(s, img, 7.05, 1.68, 5.65, 4.85, alt=alt)
    footer(s, n)


def slide_gitops(prs, n):
    s = blank(prs)
    header(s, "09 · GITOPS", "Git is the single source of truth")
    boxes = [
        (1.0, 3.1, "Git repo", "helm chart + manifests\n(versioned, reviewable)", PANEL, PANEL_B, INK, MUTED),
        (4.9, 3.2, "ArgoCD", "watches the repo,\nreconciles the cluster", ACCENT, None, WHITE, "DBEAFE"),
        (8.95, 3.4, "Kubernetes", "desired state applied\ncontinuously", PANEL, PANEL_B, INK, MUTED),
    ]
    yb, hb = 2.62, 1.5
    for x, w, name, sub, fill, line, tc, sc in boxes:
        rect(s, x, yb, w, hb, fill=fill, line=line,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.10)
        tb(s, x + 0.22, yb + 0.34, w - 0.44, 0.85,
           [{"text": name, "size": 19, "bold": True, "color": tc},
            {"text": sub, "size": 11.5, "color": sc, "line": 1.1, "before": 5}])
    for ax in (4.14, 8.14):
        rect(s, ax, yb + hb / 2 - 0.16, 0.72, 0.32, fill=SKY,
             shape=MSO_SHAPE.RIGHT_ARROW)
    rect(s, 4.9, 4.34, 3.2, 0.56, fill="DCFCE7", line="86EFAC",
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
    tb(s, 4.9, 4.46, 3.2, 0.34,
       [{"text": "●  Synced  ·  Healthy", "size": 13, "bold": True,
         "color": GREEN, "align": PP_ALIGN.CENTER}])
    bullets(s, ML, 5.24, 12.1, [
        ("Declarative, versioned, auditable", "The desired cluster state lives in Git alongside the code."),
        ("Self-correcting", "Drift is detected and reconciled automatically; rollback is a git revert."),
    ])
    footer(s, n)


def slide_results(prs, n):
    s = blank(prs, dark=True)
    header(s, "11 · RESULTS", "Proof, not promises", dark=True)
    stats = [("85", "tests passing"), ("0", "HIGH / CRITICAL"), ("5", "pods running"),
             ("27", "Terraform resources"), ("9", "Grafana panels")]
    cw, gap = 2.25, 0.22
    x = (W - (5 * cw + 4 * gap)) / 2
    for val, label in stats:
        rect(s, x, 2.15, cw, 1.85, fill=DARK_PANEL, line=DARK_BORDER,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
        tb(s, x, 2.44, cw, 0.95,
           [{"text": val, "size": 40, "bold": True, "color": SKY_L,
             "align": PP_ALIGN.CENTER}])
        tb(s, x + 0.15, 3.44, cw - 0.3, 0.5,
           [{"text": label, "size": 12, "color": DARK_MUTED, "align": PP_ALIGN.CENTER}])
        x += cw + gap
    tb(s, ML, 4.42, 12.1, 0.8,
       [{"text": "The running app displays its own commit SHA — live proof that source, "
                 "CI, registry, and cluster agree.", "size": 15, "color": DARK_TEXT,
         "align": PP_ALIGN.CENTER, "line": 1.2}])
    rect(s, (W - 5.4) / 2, 5.45, 5.4, 0.62, fill=ACCENT,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
    tb(s, (W - 5.4) / 2, 5.58, 5.4, 0.4,
       [{"text": REPO, "size": 15, "bold": True, "color": WHITE,
         "align": PP_ALIGN.CENTER}])
    footer(s, n)


def build():
    prs = new_deck()
    slide_title(prs)
    slide_product(prs, 2)
    slide_arch(prs, 3)
    slide_stack(prs, 4)
    slide_split(prs, 5, "04 · CONTAINERS", "Small images, least privilege",
                "Reviewed Dockerfiles that ship only what runs.",
                [("Multi-stage builds", "Compilers and build tools never reach the runtime image."),
                 ("Non-root runtime", "Backend runs as uid 1001, frontend as uid 101."),
                 ("Pinned bases + health checks", "Predictable builds and probe-ready containers.")],
                "11-non-root-users.png",
                "Terminal showing non-root users inside the running containers")
    slide_split(prs, 6, "05 · CI / CD", "Three gated jobs, one green path",
                "Every push runs the same pipeline; each job blocks the next.",
                [("backend-test", "85 pytest tests plus ruff lint must pass first."),
                 ("frontend-build", "Production bundle is built and checked."),
                 ("docker", "Images are built and pushed to GHCR."),
                 ("SHA-tagged, never :latest", "Each image carries its commit SHA for traceability.")],
                "14-github-actions-green.png",
                "GitHub Actions run showing all pipeline jobs green")
    slide_split(prs, 7, "06 · SECURITY", "Security is a gate, not an afterthought",
                "Trivy runs inside CI, before anything is published.",
                [("Scanned in the pipeline", "Both images are scanned for known vulnerabilities."),
                 ("Fail on HIGH / CRITICAL", "A serious finding stops the build and the publish."),
                 ("Clean result shipped", "The released images report 0 HIGH / 0 CRITICAL.")],
                "12-trivy-clean.png",
                "Trivy scan output reporting zero HIGH and CRITICAL vulnerabilities")
    slide_split(prs, 8, "07 · INFRASTRUCTURE AS CODE", "Infrastructure defined once, in code",
                "Terraform builds and tears down the AWS foundation.",
                [("Networking", "VPC with 2 public + 2 private subnets and an Internet Gateway."),
                 ("Compute", "Amazon EKS 1.36 with a managed worker node group."),
                 ("27 resources, one plan", "Provisioned by terraform apply, removed by destroy.")],
                "18-aws-eks-cluster.png",
                "AWS console showing the EKS cluster provisioned by Terraform")
    slide_split(prs, 9, "08 · KUBERNETES", "Declarative deploys that roll, not break",
                "One Helm chart describes the whole application.",
                [("A chart, not a script", "Frontend, backend and PostgreSQL defined as templates."),
                 ("5 pods running", "Two backend, two frontend, one database replica."),
                 ("Zero-downtime updates", "Rolling updates with maxUnavailable 0, ClusterIP services, nginx Ingress.")],
                "20-kubectl-resources.png",
                "kubectl output listing running pods, services and ingress")
    slide_gitops(prs, 10)
    slide_split(prs, 11, "10 · OBSERVABILITY", "If it runs, it is measured",
                "Metrics close the loop from request to container.",
                [("Prometheus scraping", "The API exposes /metrics; target clinicdesk-api reports UP."),
                 ("Grafana dashboard", "Nine live panels covering throughput, latency, errors, DB and resources."),
                 ("Proves the pipeline", "Dashboards read the same instance CI deployed.")],
                "26-grafana-dashboard.png",
                "Grafana dashboard with nine live application and infrastructure panels")
    slide_results(prs, 12)

    prs.core_properties.title = "ClinicDesk — DevOps Capstone"
    prs.core_properties.author = "ClinicDesk DevOps Capstone"
    prs.core_properties.subject = "End-to-end DevOps delivery pipeline"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)
    print("slides:", len(prs.slides._sldIdLst))
    print("saved:", OUT)


if __name__ == "__main__":
    build()
