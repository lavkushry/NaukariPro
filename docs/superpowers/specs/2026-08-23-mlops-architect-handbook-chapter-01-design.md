# MLOps Architect Handbook Chapter 1 Design

## Status

- **State:** Approved design, pending implementation-plan approval
- **Date:** August 23, 2026
- **Audience:** Senior, Staff, and Principal MLOps / ML Platform Architects
- **Initial milestone:** Publishing framework plus a publication-quality Chapter 1

## Table of Contents

1. [Objective](#objective)
2. [Scope](#scope)
3. [Source Preservation](#source-preservation)
4. [Information Architecture](#information-architecture)
5. [Chapter 1 Definition](#chapter-1-definition)
6. [Editorial Model](#editorial-model)
7. [Evidence Model](#evidence-model)
8. [Diagram Model](#diagram-model)
9. [Validation Design](#validation-design)
10. [Chapter Lifecycle](#chapter-lifecycle)
11. [Acceptance Criteria](#acceptance-criteria)
12. [Failure Handling](#failure-handling)
13. [Future Extension](#future-extension)
14. [Changelog](#changelog)

## Objective

Create a research-backed, modular MLOps Architect Handbook beginning with Chapter 1. Establish Chapter 1 as the editorial, technical, evidence, and verification standard for later chapters while preserving `mlops/vol1.md` unchanged as append-only raw source material.

## Scope

### Included

- A separate maintained handbook under `mlops/architect-handbook/`.
- Publishing documentation, editorial status, style rules, glossary, sources, diagrams, and validation tooling.
- A fully researched Chapter 1 for Senior/Staff/Principal readers.
- Claim-level evidence tracking and authoritative citations.
- Automated checks for structural, editorial, and reference defects.
- Independent specialist-agent review before publication-ready status.

### Excluded from the Initial Milestone

- Editing, renaming, truncating, formatting, or otherwise modifying `mlops/vol1.md`.
- Extracting or polishing Chapters 10 onward.
- Writing Chapters 2 onward.
- Producing PDF, EPUB, or a consolidated monolithic edition.
- Publishing or uploading the handbook.
- Treating Chapter 32 or later previews in the growing raw manuscript as stable content.

## Source Preservation

`mlops/vol1.md` is an append-only raw manuscript that may change concurrently. The initial milestone must not write to it and does not require it to remain static. Record its hash, byte size, line count, and modification time at the start and end of each milestone so external growth is visible. Any future extraction workflow must record source hashes and chapter boundaries before processing, and must operate on a frozen snapshot rather than a live-changing file.

## Information Architecture

```text
mlops/architect-handbook/
├── README.md
├── EDITORIAL_STATUS.md
├── STYLE_GUIDE.md
├── GLOSSARY.md
├── CHANGELOG.md
├── chapters/
│   └── 01-mlops-architecture-foundations.md
├── sources/
│   ├── references.md
│   └── claim-ledger.csv
├── diagrams/
│   └── chapter-01/
└── scripts/
    └── validate_handbook.sh
```

### Component Responsibilities

- `README.md`: audience, scope, reading guidance, linked table of contents, publication status, and contribution workflow.
- `EDITORIAL_STATUS.md`: chapter lifecycle states and evidence/review status.
- `STYLE_GUIDE.md`: canonical structure, heading rules, terminology, evidence, diagrams, examples, and voice.
- `GLOSSARY.md`: controlled terms, acronyms, definitions, aliases, and authoritative sources.
- `CHANGELOG.md`: material handbook changes by date.
- `chapters/`: maintained chapter sources.
- `sources/references.md`: human-readable authoritative bibliography.
- `sources/claim-ledger.csv`: claim-level evidence and review metadata.
- `diagrams/`: text-based, editable diagrams with captions, provenance, and alternative text.
- `scripts/validate_handbook.sh`: repeatable structural and editorial checks.

## Chapter 1 Definition

### Canonical Title

**MLOps Architecture Foundations: From ML Lifecycle to Enterprise Platform Strategy**

### Required Sections

1. Reader outcomes and prerequisites
2. Why production ML is a systems problem
3. ML lifecycle and operational feedback loops
4. Architecture planes
5. MLOps capability and maturity model
6. System-of-record boundaries
7. Platform and product-team responsibilities
8. Build, buy, and managed-service decisions
9. Senior, Staff, and Principal decision scope
10. Reference architecture and lifecycle flows
11. Production failure case study
12. Architecture decision record exercise
13. Interview questions and evaluation rubric
14. Key takeaways
15. Glossary additions and authoritative references

### Required Treatment per Major Concept

- Concrete production example
- Constraints and assumptions
- Architectural trade-offs
- Failure modes and recovery implications
- Security and governance implications
- Reliability and cost considerations
- Explicit boundaries with later chapters

## Editorial Model

Use a sharp, practical engineering voice. Lead with systems, artifacts, incidents, diagrams, or decisions. Explain after the concrete example. Remove generic AI transitions, inflated claims, repetitive summaries, and code fences that merely contain prose lists.

Use the hierarchy:

```text
# Chapter title
## Major section
### Subsection
#### Limited detail subsection, only when necessary
```

Each section must have one clear purpose. Acronyms must be expanded at first use. Senior/Staff/Principal distinctions must reflect scope of decisions, cross-team influence, organizational constraints, and long-term platform evolution rather than exaggerated scale.

## Evidence Model

### Claim Ledger Fields

```text
claim_id,chapter,section,claim_text,claim_type,risk_level,source_keys,source_version,source_date,accessed_date,status,review_by,notes
```

### Claim Classes

- Normative or regulatory
- Quantitative
- Product or version behavior
- Scientific or algorithmic
- Security or safety
- Architectural synthesis
- Scenario or estimate
- Opinion or heuristic

### Source Priority

1. Laws, regulators, standards, RFCs, and official specifications
2. First-party documentation, release notes, and source repositories
3. Peer-reviewed papers and canonical technical literature
4. Reputable engineering publications with disclosed systems and methodology
5. Vendor material only for claims about that vendor

Quantitative claims require reproducible calculations or primary evidence. Product behavior must be version-pinned. Security claims should prioritize NIST, CISA, OWASP, MITRE, SLSA, Sigstore, and relevant official documentation. Architectural judgment must be labeled as synthesis rather than attributed to an unrelated citation.

Volatile claims require an `as of` date and a review deadline. Unqualified language such as `best`, `always`, `never`, `guaranteed`, `latest`, and `currently` must be removed, sourced, or explicitly constrained.

## Diagram Model

Chapter 1 must include text-based architecture diagrams for the ML lifecycle, architecture planes, system-of-record relationships, and at least one failure flow. Each diagram requires:

- Figure identifier and caption
- Purpose and assumptions
- Legend where symbols are not self-evident
- Provenance: original synthesis or adapted source
- Text alternative
- Semantic review for correct directionality and responsibility boundaries

## Validation Design

`validate_handbook.sh` must fail with a non-zero exit status when required conditions are violated. It must check:

- Required files and Chapter 1 sections
- Valid heading hierarchy
- Balanced fenced blocks
- Resolvable internal Markdown links and glossary anchors
- Absence of generated fence attributes such as `id="..."`
- Absence of unresolved `TODO`, `TBD`, `FIXME`, `VERIFY`, and placeholder text
- Absence of banned generic phrases and unsupported superlatives
- Required changelog sections in maintained Markdown files where workspace rules require them
- Required claim-ledger fields and no unresolved high-risk Chapter 1 claims

Validation must not modify files. Checks must be deterministic and runnable locally without network access. Research freshness and citation entailment remain reviewer gates because they cannot be proven by syntax checks alone.

## Chapter Lifecycle

```text
Planned -> Researching -> Draft -> Technical Review -> Editorial Review -> Verified -> Publication Ready
```

A chapter may enter `Publication Ready` only when all automated checks pass, all high-risk claims are verified, diagrams are reviewed, and an independent specialist review finds no unresolved critical issue.

## Acceptance Criteria

- No implementation command or patch writes to `mlops/vol1.md`; its start and end hash, byte size, line count, and modification time are recorded, and externally appended content is reported without rollback.
- All specified handbook files exist and have clear responsibilities.
- Chapter 1 contains every required section and treatment dimension.
- Every quantitative, security, compatibility, normative, and product-behavior claim has supporting evidence.
- All citations support the exact claim and use stable, authoritative links.
- All diagrams include captions, provenance, and text alternatives.
- All automated validations pass with zero failures.
- No unresolved placeholders, unsupported superlatives, generated IDs, broken links, or unbalanced fences remain.
- Independent technical and editorial reviews approve Chapter 1.
- `EDITORIAL_STATUS.md` accurately reports the chapter state.
- Maintained documents contain current changelog entries.

## Failure Handling

- If the raw manuscript changes during work, record its new metadata and continue because Chapter 1 is newly authored and does not depend on a frozen raw snapshot; do not alter or roll back the raw file.
- If a claim lacks authoritative evidence, remove it, narrow it, or label it as a bounded author judgment.
- If sources conflict, document the disagreement and scope the claim rather than selecting the most convenient source.
- If a diagram cannot be validated, keep the chapter out of `Publication Ready`.
- If automated and reviewer assessments disagree, the stricter outcome controls until the discrepancy is resolved.

## Future Extension

After Chapter 1 is accepted, later milestones will add chapters sequentially. Chapters 2–9 and 12 will be newly authored. Existing raw chapters will be extracted only from stable snapshots, then semantically reviewed, researched, consolidated, and validated against the Chapter 1 standard.

## Changelog

### August 23, 2026

- Created the approved design for the modular handbook framework and Chapter 1 milestone.
- Defined source preservation, content structure, evidence requirements, diagrams, lifecycle states, validation, and acceptance criteria.
- Revised raw-source integrity checks to support concurrent append-only growth without permitting implementation writes.
