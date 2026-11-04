# P5 — Cover Letter (v{{version}})

Write a short cover letter using only candidate facts and the job title/company.
No fabricated achievements. Max 180 words.
If a claim cannot be grounded in facts, omit it and list it under unsupported_claims
(prefer empty cover_letter over invention).

## Facts
{{candidate_facts}}

## Job
- company: {{company}}
- title: {{title}}
- must_haves: {{must_haves}}

## Output JSON contract
- cover_letter: string (facts only; "" if nothing grounded)
- claims_used: list of evidence refs / fact snippets used
- unsupported_claims: list of claims considered but dropped (usually [])
- word_count: integer
- provider: model/provider id when LLM-produced
