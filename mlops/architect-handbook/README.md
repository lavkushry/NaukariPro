# MLOps Architect Handbook

## Reader contract

This maintained handbook serves Senior, Staff, and Principal machine learning operations (MLOps) / machine learning (ML) Platform Architects who make cross-team decisions about ML systems, platform boundaries, operational controls, and long-term architecture. It favors explicit constraints, evidence, trade-offs, failure recovery, security, cost, and operational ownership over product catalogues or unsupported prescriptions.

## Chapter 1 milestone

The initial milestone establishes the publication framework and the contract for Chapter 1, **MLOps Architecture Foundations: From ML Lifecycle to Enterprise Platform Strategy**. Chapter 1 is `Publication Ready`: independent technical, evidence, and editorial review gates are approved with zero open findings, all four diagrams are technically approved, and the final automated and rendered-diagram checks pass.

## Raw-source preservation

[`../vol1.md`](../vol1.md) is append-only raw source material outside this handbook's editing scope. Do not write to, rename, move, truncate, format, or roll back that file. Record its SHA-256, byte size, line count, and modification time at milestone checkpoints; concurrent external growth is recorded, not reversed. Any future extraction operates from a frozen, recorded observation.

## Table of contents

1. [Reader contract](#reader-contract)
2. [Chapter 1 milestone](#chapter-1-milestone)
3. [Raw-source preservation](#raw-source-preservation)
4. [Reading paths](#reading-paths)
5. [Evidence and publication policy](#evidence-and-publication-policy)
6. [Handbook map](#handbook-map)
7. [Contribution workflow](#contribution-workflow)

## Reading paths

- **Architecture decision path:** Read the Chapter 1 template in [the style guide](STYLE_GUIDE.md), the [diagram registry](diagrams/chapter-01/README.md), then the [evidence policy](#evidence-and-publication-policy) before evaluating a platform decision.
- **Evidence review path:** Read [the claim ledger](sources/claim-ledger.csv), [the bibliography](sources/references.md), the [glossary](GLOSSARY.md), and [editorial status](EDITORIAL_STATUS.md) to assess claim support and review gates.
- **Publication review path:** Read [editorial status](EDITORIAL_STATUS.md), apply [the style guide](STYLE_GUIDE.md), and run the local validator with the relevant profile.

## Evidence and publication policy

Factual claims require claim-level evidence appropriate to their risk. Label architectural judgments as `Handbook synthesis`, distinguish them from sourced facts, reproducible calculations, and illustrative scenarios, and version-pin volatile product behavior with an `as of` date and review deadline. Publication status advances only through the lifecycle in [editorial status](EDITORIAL_STATUS.md), after automated checks, evidence review, diagram review, and independent technical and editorial review.

Chapter 1 contains 72 claims: 18 P0 and 28 P1 claims are verified; 14 P2 claims are verified; and 12 P2 architectural syntheses are qualified. The qualified syntheses were independently reviewed for technical correctness, evidence boundaries, and editorial clarity, but they remain qualified and are not described as externally verified.

## Handbook map

- [Chapter 1: MLOps Architecture Foundations: From ML Lifecycle to Enterprise Platform Strategy](chapters/01-mlops-architecture-foundations.md): Defines the predictive-ML lifecycle, architecture planes, authority boundaries, operating responsibilities, and decision scope; prerequisites are source control, data pipelines, model training and evaluation, deployment, identity, telemetry, and incident-response fundamentals; state is `Publication Ready`, with technical, evidence, editorial, diagram, validator, and render gates complete.
- [Editorial status](EDITORIAL_STATUS.md): lifecycle, chapter register, and raw-source observations.
- [Style guide](STYLE_GUIDE.md): binding chapter template and editorial rules.
- [Glossary](GLOSSARY.md): controlled architectural vocabulary and verification state.
- [References](sources/references.md): authoritative bibliography and source-key convention.
- [Claim ledger](sources/claim-ledger.csv): claim-level evidence and review metadata.
- [Chapter 1 diagrams](diagrams/chapter-01/README.md): figure registry and review metadata.
- [Handbook changelog](CHANGELOG.md): maintained publication-framework changes.

## Contribution workflow

1. Start with a read-only raw-source observation if source extraction is in scope.
2. Research and record claims before drafting factual prose.
3. Draft to the canonical chapter template and register diagrams before reference.
4. Run local structure validation during framework work and release validation only when its required content exists.
5. Advance editorial status only after the corresponding evidence and review gates are satisfied.

## Changelog

### 2026-08-23

- Advanced Chapter 1 sequentially from `Technical Review` to `Editorial Review`, `Verified`, and `Publication Ready` after the corresponding independent approvals, final validators, and rendered-diagram checks passed.
- Recorded 72 claims without conflating reviewed synthesis with external verification: P0 18 verified; P1 28 verified; P2 14 verified and 12 qualified.
- Linked the architecture decision reading path directly to the evidence and publication policy.
- Synchronized the Chapter 1 map with the pending technical and editorial rereview gates without advancing its `Technical Review` state.
- Expanded the scaffold into the reader contract, navigation map, reading paths, raw-source rule, and evidence-based publication policy.
- Linked the completed Chapter 1 draft with its purpose, prerequisites, and honest `Technical Review` state; added no links to unwritten chapters.
