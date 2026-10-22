# Handbook Style Guide

## Purpose and scope

This guide is the binding editorial contract for maintained handbook chapters. It applies to prose, diagrams, examples, citations, and exercises written for Senior, Staff, and Principal MLOps / ML Platform Architects.

## Voice and audience

Lead with a system boundary, artifact, incident, diagram, or decision. State the engineering context before analysis. Explain implications with precise language, bounded assumptions, and explicit ownership. Distinguish Senior, Staff, and Principal scope through decision horizon, cross-team influence, organizational constraints, and platform evolution; do not imply scale that evidence does not support.

## Canonical chapter template

Each chapter has one H1 and follows the approved sequence below. A section may contain H3 and H4 detail only when it clarifies a discrete decision, interface, or failure boundary. Do not reorder, omit, or add a peer H2 without an approved editorial change.

```text
# Chapter N: Title
## Reader outcomes and prerequisites
## Why production ML is a systems problem
## ML lifecycle and operational feedback loops
## Architecture planes
## MLOps capability and maturity model
## System-of-record boundaries
## Platform and product-team responsibilities
## Build, buy, and managed-service decisions
## Senior, Staff, and Principal decision scope
## Reference architecture and lifecycle flows
## Production failure case study
## Architecture decision record exercise
## Interview questions and evaluation rubric
## Key takeaways
## Glossary additions and authoritative references
### Decision or implementation detail
#### Narrow exception or interface detail
```

Where a major concept has enough substance, use this treatment order:

```text
problem -> constraints -> architecture -> trade-offs -> failure modes -> security -> cost -> operations -> decision framework -> exercises
```

The order is a reasoning pattern, not permission to add unneeded headings. State the boundary with later chapters when a concept is introduced but not fully developed.

## Heading and terminology rules

- Use ATX headings: one `#` chapter title, `##` major sections, `###` subsections, and `####` only for necessary detail.
- Do not skip heading levels, create a second H1, or use generated heading identifiers.
- Expand an acronym at first use in each chapter and in its glossary definition, then use the shortened form consistently. Example: `machine learning (ML)` and `machine learning operations (MLOps)`.
- Define a controlled term through [the glossary](GLOSSARY.md) before treating it as a stable handbook term.

## Evidence, citations, and synthesis

Use a claim ledger row for each factual claim that is quantitative, normative, product- or version-specific, scientific, security-related, or safety-related. Cite sources in prose with the stable key from [the bibliography](sources/references.md), for example `NIST-AI-RMF-2023`, and place the same key in the ledger's `source_keys` field.

Use one of the following labels at the point of use:

- **Sourced fact:** A claim supported by a source key whose source entails the stated claim.
- **Reproducible calculation:** A calculation with inputs, method, units, and source keys recorded.
- **Illustrative scenario:** A bounded example that is not reported production evidence.
- **Handbook synthesis:** An architectural judgment that combines stated assumptions and trade-offs; it is not presented as an externally verified fact.

Version-pin product behavior and include an `as of` date plus a review deadline in the ledger. Prefer laws, standards, official specifications, first-party documentation, and peer-reviewed work. A vendor source supports claims about that vendor, not a general industry claim.

## Examples and callouts

Use examples to make a decision or interface testable. Identify whether an example is sourced, calculated, illustrative, or synthesis, then include its assumptions and the decision it informs. Do not use code fences for prose-only lists.

Use this callout syntax:

```markdown
> **Decision:** State the decision and its owner.
>
> **Assumptions:** State the constraints that make the decision applicable.
>
> **Trade-off:** State the benefit, cost, and rejected alternative.
```

Use this example syntax:

```markdown
**Illustrative scenario:** A product team selects a model registry as the approval boundary.

**Assumptions:** The scenario is a handbook synthesis and does not report an observed deployment.
```

## Diagram and reference rules

Keep diagrams text-based and editable. Register each figure in [the Chapter 1 diagram registry](diagrams/chapter-01/README.md) before it is referenced by chapter prose. A figure requires a caption, purpose, assumptions, legend where symbols need explanation, provenance, text alternative, semantic reviewer, and review status. Review directionality and responsibility boundaries before an editorial state can advance.

Use CommonMark-compatible relative links for maintained files. Cite a diagram by its figure ID and include a readable caption in the surrounding prose.

## Banned generic phrasing and unsupported claims

Do not use generic transitions, inflated framing, repetitive wrap-ups, or unbounded superlatives in chapter prose. The validation policy recognizes the following examples; this fenced block documents the policy and is not approved copy.

```text
game-changer
cutting-edge
revolutionary
in today's rapidly evolving landscape
in the ever-evolving world
in the ever-evolving landscape
it is important to note
it is worth noting
in conclusion
to summarize
as we delve into
this section will explore
this section will discuss
this section will cover
this comprehensive guide
in the realm of
best
always
never
guaranteed
latest
currently
```

Replace vague transitions with the system condition, decision, evidence, or consequence. Constrain a comparative or temporal claim with a source, an `as of` date, or an explicit scenario boundary.

## Publication checks

Before a chapter advances, confirm that its headings, fences, links, markers, placeholder forms, generic phrases, superlatives, changelog, diagrams, citations, and claim-ledger state pass the applicable local validation profile. Automated validation is necessary but does not replace evidence-entailment or semantic diagram review.

## Changelog

### 2026-08-23

- Replaced the scaffold rules with the binding chapter template, evidence labels, citation convention, example and callout formats, diagram rules, and editorial policy.
