"""ATS-safe single-column PDF (ReportLab) + DOCX (python-docx)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape as _xml_escape


def _safe_filename(name: str, role: str, company: str) -> str:
    def scrub(s: str) -> str:
        s = re.sub(r"[^\w\s\-]+", "", s or "")
        return re.sub(r"\s+", "_", s.strip())[:40] or "X"

    return f"{scrub(name)}_{scrub(role)}_{scrub(company)}"


def _norm_url(raw_url: Any) -> str:
    s = str(raw_url or "").strip()
    if not s:
        return ""
    if not s.startswith(("http://", "https://")):
        return f"https://{s.lstrip('/')}"
    return s


def _format_role_dates(role_obj: Dict[str, Any]) -> str:
    explicit = (role_obj.get("dates") or role_obj.get("duration") or "").strip()
    if explicit:
        return explicit
    start = str(role_obj.get("start") or "").strip()
    end = str(role_obj.get("end") or "").strip()
    if start and end:
        return f"{start} – {end}"
    return start or end


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
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate

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
    story.append(Paragraph(_xml_escape(str(name)), name_style))

    loc = candidate.get("location") or candidate.get("primary_location")
    phone = candidate.get("phone")
    email = str(candidate.get("email") or "").strip()
    linkedin = _norm_url(candidate.get("linkedin"))
    github = _norm_url(candidate.get("github"))

    contact_parts: List[str] = []
    if loc:
        contact_parts.append(_xml_escape(str(loc)))
    if phone:
        contact_parts.append(_xml_escape(str(phone)))
    if email:
        safe_email = _xml_escape(email)
        contact_parts.append(f'<link href="mailto:{safe_email}" color="#11355D">{safe_email}</link>')
    if linkedin:
        safe_li = _xml_escape(linkedin)
        li_label = _xml_escape(linkedin.replace("https://www.", "").replace("https://", "").rstrip("/"))
        contact_parts.append(f'<link href="{safe_li}" color="#11355D">{li_label}</link>')
    if github:
        safe_gh = _xml_escape(github)
        gh_label = _xml_escape(github.replace("https://", "").rstrip("/"))
        contact_parts.append(f'<link href="{safe_gh}" color="#11355D">{gh_label}</link>')

    story.append(Paragraph(" | ".join(contact_parts), contact))
    story.append(HRFlowable(width="100%", thickness=0.5, spaceAfter=6))

    sections = {s["name"]: s.get("content") for s in (tailored.get("tailored_sections") or []) if isinstance(s, dict)}

    summary = sections.get("summary") or candidate.get("summary") or ""
    if summary:
        story.append(Paragraph("PROFESSIONAL SUMMARY", h2))
        story.append(Paragraph(_xml_escape(str(summary)), body))

    skills = sections.get("skills") or []
    if skills:
        story.append(Paragraph("TECHNICAL SKILLS", h2))
        if isinstance(skills, list):
            story.append(Paragraph(_xml_escape(", ".join(str(s) for s in skills)), body))
        else:
            story.append(Paragraph(_xml_escape(str(skills)), body))

    story.append(Paragraph("PROFESSIONAL EXPERIENCE", h2))
    exp = sections.get("experience") or []
    bullets = sections.get("experience_bullets") or []
    if isinstance(exp, list) and exp:
        for role_obj in exp:
            if not isinstance(role_obj, dict):
                continue
            title = _xml_escape(str(role_obj.get("title") or role_obj.get("role") or ""))
            company_n = _xml_escape(str(role_obj.get("company") or role_obj.get("employer") or ""))
            dates = _xml_escape(_format_role_dates(role_obj))
            date_suffix = f" ({dates})" if dates else ""
            story.append(Paragraph(f"<b>{title}</b> — {company_n}{date_suffix}", body))
            for b in role_obj.get("bullets") or role_obj.get("highlights") or []:
                story.append(Paragraph(f"• {_xml_escape(str(b))}", body))
    elif bullets:
        for b in bullets:
            story.append(Paragraph(f"• {_xml_escape(str(b))}", body))

    projects = sections.get("projects") or []
    if isinstance(projects, list) and projects:
        story.append(Paragraph("KEY PROJECTS", h2))
        for proj in projects:
            if isinstance(proj, dict):
                pname = _xml_escape(str(proj.get("name") or ""))
                ptech = _xml_escape(str(proj.get("tech_stack") or ""))
                purl = _norm_url(proj.get("url"))
                if purl:
                    safe_purl = _xml_escape(purl)
                    header = f'<link href="{safe_purl}" color="#11355D"><b>{pname}</b></link>'
                else:
                    header = f"<b>{pname}</b>"
                if ptech:
                    header += f" ({ptech})"
                if purl:
                    safe_purl = _xml_escape(purl)
                    header += f' — <link href="{safe_purl}" color="#11355D">GitHub</link>'
                story.append(Paragraph(header, body))
                for pb in proj.get("bullets") or []:
                    story.append(Paragraph(f"• {_xml_escape(str(pb))}", body))
            else:
                story.append(Paragraph(f"• {_xml_escape(str(proj))}", body))

    edu = sections.get("education") or []
    if edu:
        story.append(Paragraph("EDUCATION", h2))
        if isinstance(edu, list):
            for e in edu:
                if isinstance(e, dict):
                    deg = _xml_escape(str(e.get("degree", "")))
                    inst = _xml_escape(str(e.get("school", e.get("institution", ""))))
                    edates = _xml_escape(str(e.get("dates", "")))
                    line = f"{deg} — {inst}" + (f" ({edates})" if edates else "")
                    story.append(Paragraph(line, body))
                else:
                    story.append(Paragraph(_xml_escape(str(e)), body))
        else:
            story.append(Paragraph(_xml_escape(str(edu)), body))

    certs = sections.get("certifications") or []
    if certs:
        story.append(Paragraph("CERTIFICATIONS", h2))
        if isinstance(certs, list):
            story.append(Paragraph(_xml_escape(", ".join(str(c) for c in certs)), body))
        else:
            story.append(Paragraph(_xml_escape(str(certs)), body))

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
        candidate.get("location") or candidate.get("primary_location"),
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
    exp = sections.get("experience") or []
    if isinstance(exp, list) and exp:
        for role_obj in exp:
            if not isinstance(role_obj, dict):
                continue
            title = role_obj.get("title") or role_obj.get("role") or ""
            company_n = role_obj.get("company") or role_obj.get("employer") or ""
            dates = _format_role_dates(role_obj)
            date_suffix = f" ({dates})" if dates else ""
            doc.add_paragraph(f"{title} — {company_n}{date_suffix}")
            for b in role_obj.get("bullets") or role_obj.get("highlights") or []:
                doc.add_paragraph(str(b), style="List Bullet")
    else:
        for b in sections.get("experience_bullets") or []:
            doc.add_paragraph(str(b), style="List Bullet")
    projects = sections.get("projects") or []
    if isinstance(projects, list) and projects:
        doc.add_heading("Key Projects", level=2)
        for proj in projects:
            if isinstance(proj, dict):
                pname = proj.get("name") or ""
                purl = proj.get("url") or ""
                doc.add_paragraph(f"{pname} ({purl})" if purl else str(pname))
                for pb in proj.get("bullets") or []:
                    doc.add_paragraph(str(pb), style="List Bullet")
            else:
                doc.add_paragraph(str(proj), style="List Bullet")
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
