# P3 — Truth-Preserving Resume Tailor (v{{version}})

Reorder and rewrite resume bullets STRICTLY from candidate facts.
Never add tools, metrics, employers, titles, or dates not in facts.
Mirror ATS keywords only when truthfully covered.
Report uncovered must-haves in gaps_reported.

## Facts
{{candidate_facts}}

## Target role requirements
{{jd_structured}}

## Output
- tailored_sections: ordered section payloads
- gaps_reported: list of uncovered must-haves
- keywords_mirrored: list (subset of truthful coverage)
