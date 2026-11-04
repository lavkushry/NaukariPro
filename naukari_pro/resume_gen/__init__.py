"""Workstream 4 — truth-preserving ATS resume generation."""

from naukari_pro.resume_gen.tailor import tailor_from_facts
from naukari_pro.resume_gen.render import render_resume_pdf, render_resume_docx
from naukari_pro.resume_gen.pipeline import ResumeGenerationPipeline

__all__ = [
    "tailor_from_facts",
    "render_resume_pdf",
    "render_resume_docx",
    "ResumeGenerationPipeline",
]
