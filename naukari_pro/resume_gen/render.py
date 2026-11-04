"""ATS-safe single-column PDF (ReportLab) + DOCX (python-docx)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_filename(name: str, role: str, company: str) -> str:
    def scrub(s: str) -> str:
        s = re.sub(r"[^\w\s\-]+", "", s or "")
        return re.sub(r"\s+", "_", s.strip())[:40] or "X"

    return f"{scrub(name)}_{scrub(role)}_{scrub(company)}"


def render_resume_pdf(
    candidate: Dict[str, Any],
    tailored: Dict[str, Any],
    *,
    output_dir: Path,
    role: str = "Role",
    company: str = "Company",
) -> Path:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = candidate.get("name") or "Candidate"
    path = output_dir / f"{_safe_filename(name, role, company)}.pdf"

    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=styles["Heading1"], fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=12)
    contact = ParagraphStyle("Contact", parent=styles["Normal"], fontSize=9, leading=11)

    story: List[Any] = []
    story.append(Paragraph(str(name), name_style))
    contact_bits = [
        candidate.get("location"),
        candidate.get("phone"),
        candidate.get("email"),
        candidate.get("linkedin"),
        candidate.get("github"),
    ]
    story.append(Paragraph(" | ".join(str(x) for x in contact_bits if x), contact))
    story.append(HRFlowable(width="100%", thickness=0.5, spaceAfter=6))

    sections = {s["name"]: s.get("content") for s in (tailored.get("tailored_sections") or []) if isinstance(s, dict)}

    summary = sections.get("summary") or candidate.get("summary") or ""
    if summary:
        story.append(Paragraph("PROFESSIONAL SUMMARY", h2))
        story.append(Paragraph(str(summary), body))

    skills = sections.get("skills") or []
    if skills:
        story.append(Paragraph("TECHNICAL SKILLS", h2))
        if isinstance(skills, list):
            story.append(Paragraph(", ".join(str(s) for s in skills), body))
        else:
            story.append(Paragraph(str(skills), body))

    story.append(Paragraph("PROFESSIONAL EXPERIENCE", h2))
    exp = sections.get("experience") or []
    bullets = sections.get("experience_bullets") or []
    if isinstance(exp, list) and exp:
        for role_obj in exp:
            if not isinstance(role_obj, dict):
                continue
            title = role_obj.get("title") or role_obj.get("role") or ""
            company_n = role_obj.get("company") or role_obj.get("employer") or ""
            dates = role_obj.get("dates") or f"{role_obj.get('start', '')} – {role_obj.get('end', '')}"
            story.append(Paragraph(f"<b>{title}</b> — {company_n} ({dates})", body))
            for b in role_obj.get("bullets") or role_obj.get("highlights") or []:
                story.append(Paragraph(f"• {b}", body))
    elif bullets:
        for b in bullets:
            story.append(Paragraph(f"• {b}", body))

    edu = sections.get("education") or []
    if edu:
        story.append(Paragraph("EDUCATION", h2))
        if isinstance(edu, list):
            for e in edu:
                story.append(Paragraph(str(e) if not isinstance(e, dict) else (
                    f"{e.get('degree', '')} — {e.get('school', e.get('institution', ''))}"
                ), body))
        else:
            story.append(Paragraph(str(edu), body))

    certs = sections.get("certifications") or []
    if certs:
        story.append(Paragraph("CERTIFICATIONS", h2))
        if isinstance(certs, list):
            story.append(Paragraph(", ".join(str(c) for c in certs), body))
        else:
            story.append(Paragraph(str(certs), body))

    doc.build(story)
    return path


def render_resume_docx(
    candidate: Dict[str, Any],
    tailored: Dict[str, Any],
    *,
    output_dir: Path,
    role: str = "Role",
    company: str = "Company",
) -> Path:
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("python-docx is required for DOCX export") from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = candidate.get("name") or "Candidate"
    path = output_dir / f"{_safe_filename(name, role, company)}.docx"
    doc = Document()
    doc.add_heading(str(name), level=1)
    contact_bits = [
        candidate.get("location"),
        candidate.get("phone"),
        candidate.get("email"),
        candidate.get("linkedin"),
        candidate.get("github"),
    ]
    doc.add_paragraph(" | ".join(str(x) for x in contact_bits if x))

    sections = {s["name"]: s.get("content") for s in (tailored.get("tailored_sections") or []) if isinstance(s, dict)}
    if sections.get("summary"):
        doc.add_heading("Professional Summary", level=2)
        doc.add_paragraph(str(sections["summary"]))
    skills = sections.get("skills") or []
    if skills:
        doc.add_heading("Technical Skills", level=2)
        doc.add_paragraph(", ".join(str(s) for s in skills) if isinstance(skills, list) else str(skills))
    doc.add_heading("Professional Experience", level=2)
    for b in sections.get("experience_bullets") or []:
        doc.add_paragraph(str(b), style="List Bullet")
    doc.save(str(path))
    return path


def pypdf_roundtrip_ok(pdf_path: Path) -> bool:
    try:
        import pypdf
    except ImportError:
        return False
    reader = pypdf.PdfReader(str(pdf_path))
    if not reader.pages:
        return False
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    return len(text.strip()) > 40
