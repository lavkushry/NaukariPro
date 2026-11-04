# P3 — Truth-Preserving Resume Tailor (v{{version}})

Reorder and lightly rewrite resume content STRICTLY from candidate facts.
Never add tools, metrics, employers, titles, certifications, or dates not in facts.
Classify JD terms into have / support / gap. Mirror ATS keywords only when truthfully covered.
Report uncovered must-haves in gaps_reported AND keyword_coverage.gap.
Empty placeholders → leave empty string / empty array — never invent.

## Facts (verbatim evidence only)
{{candidate_facts}}

## Target role requirements (structured JD)
{{jd_structured}}

## Output JSON contract
- summary: one short paragraph using only facts (or "")
- tailored_sections: ordered section payloads `{name, content}` (keep experience_bullets exact fact strings)
- experience: roles reordered by JD relevance; bullets must be verbatim from facts
- skills_ordered: existing skills only, JD-overlap first
- keyword_coverage: `{have, support, gap}` term lists
- gaps_reported: uncovered must-haves
- keywords_mirrored: subset of truthful coverage
- scorer: "llm" when model-produced
