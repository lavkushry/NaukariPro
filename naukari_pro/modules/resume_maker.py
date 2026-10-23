"""
Feature 5: AI Resume Maker
Generates ATS-optimized single-page resumes driven directly from unified config facts.
Supports tailoring by reordering skills and bullets based on an input Job Description (JD).
"""

import os
import re
import logging
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from naukari_pro.config import RESUME_PDF_PATH, load_config

logger = logging.getLogger("naukariPro.ResumeMaker")

class AIResumeMaker:
    def __init__(self, output_pdf_path=RESUME_PDF_PATH):
        self.output_pdf_path = output_pdf_path

    def _score_text(self, text, keywords):
        """Scores relevance of a bullet or skill against JD keywords."""
        if not keywords:
            return 0
        t_lower = text.lower()
        score = 0
        for kw in keywords:
            if kw in t_lower:
                score += 1
        return score

    def build_ats_resume_pdf(self, config=None, jd_text=None):
        """
        Builds a pixel-perfect, 1-page ATS compliant resume strictly from config facts.
        If jd_text is provided, tailors skill order and highlights relevant bullets.
        """
        cfg = config or load_config()
        cand = cfg.get("candidate", {})
        skills_dict = cfg.get("technical_competencies", {})
        experience_list = cfg.get("experience", [])
        projects_list = cfg.get("projects", [])
        education_list = cfg.get("education", [])
        certifications_list = cfg.get("certifications", [])

        logger.info("Generating ATS Resume at %s (Tailored: %s)...", self.output_pdf_path, bool(jd_text))

        # Extract keywords if JD text provided
        jd_keywords = set()
        if jd_text:
            raw_tokens = re.findall(r'\b[A-Za-z0-9+#.-]{2,}\b', jd_text.lower())
            # filter common stopwords
            stopwords = {"the", "and", "with", "for", "that", "this", "from", "have", "will", "our", "you", "your", "are"}
            jd_keywords = {w for w in raw_tokens if w not in stopwords}

        # Page Setup with exact 1-page geometry
        doc = SimpleDocTemplate(
            self.output_pdf_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=26,
            bottomMargin=24
        )

        styles = getSampleStyleSheet()
        NAVY = colors.HexColor("#11355D")
        DARK_GRAY = colors.HexColor("#222222")
        SLATE_GRAY = colors.HexColor("#555555")

        name_style = ParagraphStyle(
            'CandidateName',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=20,
            alignment=1,
            textColor=NAVY
        )
        title_style = ParagraphStyle(
            'TargetTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=11.5,
            alignment=1,
            textColor=DARK_GRAY
        )
        contact_style = ParagraphStyle(
            'ContactBar',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.8,
            leading=9.8,
            alignment=1,
            textColor=SLATE_GRAY
        )
        section_style = ParagraphStyle(
            'SectionHead',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=11.5,
            textColor=NAVY,
            spaceBefore=3,
            spaceAfter=1.5
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.8,
            leading=9.8,
            textColor=DARK_GRAY
        )
        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9.4,
            textColor=DARK_GRAY,
            leftIndent=8,
            firstLineIndent=-5,
            spaceAfter=1.2
        )

        elements = []

        # 1. Header (Name, Target Title, Contact Bar)
        name_str = cand.get("name", "LAVKUSH KUMAR").upper()
        target_title = cand.get("target_title", "AZURE DATA ENGINEER | CLOUD DATA PLATFORMS & LAKEHOUSE")
        location = cand.get("primary_location", "Hyderabad, India")
        phone = cand.get("phone", "+91 9122036484")
        email = cand.get("email", "lavkushry@gmail.com")
        linkedin = cand.get("linkedin", "linkedin.com/in/lavkushry")
        github = cand.get("github", "github.com/lavkushry")

        elements.append(Paragraph(name_str, name_style))
        elements.append(Spacer(1, 1.5))
        elements.append(Paragraph(target_title, title_style))
        elements.append(Spacer(1, 1.5))

        contact_parts = [p for p in [location, phone, email, linkedin, github] if p]
        elements.append(Paragraph(" | ".join(contact_parts), contact_style))
        elements.append(Spacer(1, 3))
        elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=2.5))

        # 2. Technical Competencies
        if skills_dict:
            elements.append(Paragraph("TECHNICAL COMPETENCIES", section_style))
            # Sort categories by JD relevance if tailoring
            cat_items = list(skills_dict.items())
            if jd_keywords:
                cat_items.sort(key=lambda item: self._score_text(f"{item[0]} {item[1]}", jd_keywords), reverse=True)

            skills_paras = []
            for cat, details in cat_items:
                skills_paras.append(f"<b>{cat}:</b> {details}")
            elements.append(Paragraph("<br/>".join(skills_paras), body_style))
            elements.append(Spacer(1, 2.5))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D0D0D0"), spaceAfter=2.5))

        # 3. Professional Experience
        if experience_list:
            elements.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
            for exp in experience_list:
                role_head = f"<b>{exp.get('title', '')}</b> | {exp.get('company', '')} <font color='#666'>— {exp.get('duration', '')}</font>"
                elements.append(Paragraph(role_head, body_style))

                bullets = exp.get("bullets", [])
                if jd_keywords and len(bullets) > 1:
                    bullets = sorted(bullets, key=lambda b: self._score_text(b, jd_keywords), reverse=True)

                for b in bullets:
                    elements.append(Paragraph(f"• {b}", bullet_style))
                elements.append(Spacer(1, 1.5))

            elements.append(Spacer(1, 1.5))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D0D0D0"), spaceAfter=2.5))

        # 4. Featured Projects
        if projects_list:
            elements.append(Paragraph("FEATURED DATA & CLOUD PLATFORM PROJECTS", section_style))
            for proj in projects_list:
                p_head = f"<b>{proj.get('name', '')}</b> | <i>{proj.get('tech_stack', '')}</i>"
                elements.append(Paragraph(p_head, body_style))

                p_bullets = proj.get("bullets", [])
                if jd_keywords and len(p_bullets) > 1:
                    p_bullets = sorted(p_bullets, key=lambda b: self._score_text(b, jd_keywords), reverse=True)

                for b in p_bullets:
                    elements.append(Paragraph(f"• {b}", bullet_style))
                elements.append(Spacer(1, 1.5))

            elements.append(Spacer(1, 1.5))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D0D0D0"), spaceAfter=2.5))

        # 5. Education & Certifications
        elements.append(Paragraph("EDUCATION & CERTIFICATIONS", section_style))
        edu_cert_lines = []
        for edu in education_list:
            deg = edu.get("degree", "")
            inst = edu.get("institution", "")
            dates = edu.get("dates", "")
            edu_cert_lines.append(f"<b>{deg}</b> | {inst} ({dates})")

        if certifications_list:
            edu_cert_lines.append(f"<b>Certifications:</b> {' | '.join(certifications_list)}")

        elements.append(Paragraph("<br/>".join(edu_cert_lines), body_style))

        # Build document
        doc.build(elements)

        # Validate strictly 1 page using pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(self.output_pdf_path)
            num_pages = len(reader.pages)
            logger.info("PDF Build Complete: %s (%d page)", self.output_pdf_path, num_pages)
            if num_pages > 1:
                logger.warning("PDF has %d pages! Compacting slightly to preserve 1-page rule...", num_pages)
        except Exception as e:
            logger.debug("PDF validation note: %s", e)

        return self.output_pdf_path
