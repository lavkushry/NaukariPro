# MLOps Architect Handbook Chapter 2 Design

## Status

- **State:** Proposed design, pending user review
- **Date:** August 24, 2026
- **Audience:** Senior, Staff, and Principal MLOps / ML Platform Architects
- **Milestone:** Publication-quality Chapter 2 plus the Chapters 2-4 roadmap boundary
- **Scope choice:** Predictive ML first; vendor-neutral architecture with concrete implementation examples

## Table of Contents

1. [Objective](#objective)
2. [Roadmap Decomposition](#roadmap-decomposition)
3. [Chapter 2 Scope](#chapter-2-scope)
4. [Source Preservation](#source-preservation)
5. [Canonical Chapter Definition](#canonical-chapter-definition)
6. [Recurring Scenario](#recurring-scenario)
7. [Architecture Model](#architecture-model)
8. [Evidence Model](#evidence-model)
9. [Diagram Model](#diagram-model)
10. [Editorial Model](#editorial-model)
11. [Validation Design](#validation-design)
12. [Review and Lifecycle](#review-and-lifecycle)
13. [File and Interface Design](#file-and-interface-design)
14. [Acceptance Criteria](#acceptance-criteria)
15. [Failure Handling](#failure-handling)
16. [Future Chapter Boundaries](#future-chapter-boundaries)
17. [Changelog](#changelog)

## Objective

Create Chapter 2 as the data and feature architecture foundation for the maintained MLOps Architect Handbook. The chapter must teach readers to design reviewable boundaries for data semantics, time, identity, feature computation, validation, lineage, governance, and recovery before training, release, or serving systems consume those facts.

Chapter 2 must match or exceed the evidence, architecture, accessibility, review, and validation standard established by publication-ready Chapter 1. It must remain useful when individual products or cloud services change.

### Canonical Title

**Data and Feature Architecture: Contracts, Point-in-Time Correctness, Parity, and Recovery**

### Reader Outcome

After completing the chapter, a reader must be able to produce and defend a data-and-feature architecture that answers:

- Which system owns each semantic fact?
- Which identity makes a dataset, feature definition, or materialization reproducible?
- Which clock and event boundary make a training example valid?
- How are batch and streaming computations kept semantically consistent?
- How are online and offline feature paths compared without assuming equality?
- Which checks block admission, training, or release?
- How are contaminated intervals bounded, quarantined, rebuilt, or discarded?
- Which obligations belong to the producer, workload team, platform, independent authority, and contracted provider?

## Roadmap Decomposition

The user-approved request covers three architecture domains. They are implemented as separate chapters so each chapter has one dominant system boundary and independent evidence/review gates.

### Chapter 2 — Data and Feature Architecture

Owns contracts, event and processing time, immutable dataset identity, snapshots, feature definitions, offline/online access, point-in-time joins, parity, validation, lineage, governance, retention, and data recovery.

### Chapter 3 — ML Delivery Control Plane

Consumes Chapter 2 dataset, feature, and evidence identities. Owns continuous integration and continuous delivery (CI/CD), continuous training (CT), orchestration, model registry and approval, desired deployment state, progressive release, rollback, and controller reconciliation.

### Chapter 4 — Model Serving and Inference Architecture

Consumes approved immutable model/runtime bundles and declared feature interfaces. Owns online and batch inference, KServe/Triton/vLLM examples, capacity, autoscaling, service-level objectives (SLOs), load shedding, progressive rollout, fallback, and inference cost.

### Deferred Domain

Retrieval-augmented generation (RAG), generative AI, vector retrieval, prompt/evaluation stores, and agentic systems remain outside Chapters 2-4. They require a later dedicated architecture milestone rather than predictive-ML concepts relabeled as GenAI guidance.

## Chapter 2 Scope

### Included

- Batch, streaming, and mixed data paths for predictive ML.
- Schema, semantic, unit, range, freshness, and ownership contracts.
- Event time, processing time, ingestion time, watermarks, late data, and correction boundaries.
- Dataset manifests, immutable snapshots, partitions, event ranges, and reproducible identities.
- Feature definitions, transformations, materializations, and ownership.
- Offline and online feature access patterns without assuming one storage product.
- Point-in-time correct joins and leakage prevention.
- Training-serving computation parity and explicitly bounded divergence.
- Admission, transformation, feature, training-input, and serving-input validation gates.
- Data and feature observability, service-level indicators (SLIs), and alert ownership.
- Lineage, canonical records, retention, deletion, access, and audit evidence.
- Backfill, quarantine, replay, normalization, rebuild, and irrecoverable-interval decisions.
- Platform/product/producer/provider responsibility contracts.
- Build, buy, managed-service, and portability decisions.
- Senior, Staff, and Principal decision horizons.

### Excluded

- Model-training algorithm selection and hyperparameter optimization.
- General pipeline-orchestrator implementation beyond data/feature interfaces.
- Model approval, deployment-controller, rollout, and rollback internals owned by Chapter 3.
- Inference-server, autoscaling, batching, GPU, and runtime internals owned by Chapter 4.
- RAG, vector databases, LLM prompt data, and agent memory architecture.
- Vendor feature matrices, price comparisons, or cloud-product catalogues.
- Invented production metrics or unbounded claims of consistency, correctness, or cost reduction.

## Source Preservation

`mlops/vol1.md` remains append-only raw source material outside the maintained handbook write scope. Chapter 2 is newly authored and must not depend on a stable live raw file.

At the Chapter 2 milestone start and end, record:

- SHA-256
- Line count
- Byte count
- Modification time

External growth is reported without rollback. No implementation command or patch may write to, rename, move, truncate, or format the raw file.

## Canonical Chapter Definition

Chapter 2 uses one H1, the following H2 sections in exact order, and a final `## Changelog`:

1. Reader outcomes and prerequisites
2. Why data semantics are a systems problem
3. Data lifecycle and time semantics
4. Data contracts and semantic evolution
5. Dataset identity, versioning, and reproducibility
6. Feature computation and offline/online architecture
7. Point-in-time correctness and training-serving parity
8. Validation, observability, and data-quality decisions
9. Lineage, governance, security, retention, and deletion
10. Platform, product, producer, and provider responsibilities
11. Reference architecture and failure-recovery flow
12. Architecture decision record exercise
13. Interview questions and evaluation rubric
14. Key takeaways
15. Glossary additions and authoritative references

### Required Treatment per Major Concept

Each major concept must include:

- A concrete artifact, decision, or incident.
- Constraints and explicitly stated assumptions.
- Authority, ownership, and canonical-record boundaries.
- Batch, streaming, and mixed-path implications where relevant.
- Security, privacy, retention, and deletion considerations.
- Reliability, recovery, cost, and operational consequences.
- Failure modes and detection signals.
- Build, buy, managed-service, and portability implications where relevant.
- Senior, Staff, and Principal decision scope.
- A forward boundary to Chapters 3 or 4 when those chapters own implementation detail.

## Recurring Scenario

Chapter 2 continues Chapter 1's fictional replenishment-ranking system so interfaces and failures remain comparable across chapters.

### Scenario Trigger

An upstream producer preserves the field name and numeric type of `inventory_age` but changes its unit from days to hours. Structural schema checks pass. Batch history and streaming events overlap during rollout, some records lack a producer revision, and delayed outcomes hide the impact.

### Scenario Questions

- Where is the semantic contract stored and who may change it?
- Which producer revision or event-time range bounds the affected interval?
- Can records be normalized safely, or must an interval be quarantined or discarded?
- How does a point-in-time join avoid mixing corrected future knowledge into historical examples?
- Which feature definition and materialization identities reproduce training and serving inputs?
- What detects training-serving disagreement when endpoint health remains green?
- Who authorizes replay, backfill, fallback, or permanent exclusion?

The scenario is always labeled illustrative. It is not presented as an observed company incident.

## Architecture Model

### Authority Boundaries

The chapter distinguishes at least these authorities:

- Producer semantic contract and revision history.
- Workload-data bytes and immutable/versioned dataset identity.
- Feature definition and transformation identity.
- Offline materialization state.
- Online materialization state.
- Validation evidence and failed-admission/quarantine state.
- Lineage and transformation-execution records.
- Access, retention, deletion, and exception decisions.
- Derived catalogues and dashboards that are not canonical records.

Records do not issue control. Named authorities decide; authorized workflows write desired or canonical facts; controllers and execution mechanisms act; observed evidence returns to records.

### Time Model

The chapter must keep event time, processing time, ingestion time, materialization time, and observation time distinct. Watermarks and lateness policies are implementation contracts, not proof of semantic correctness. Point-in-time correctness must state the observation cutoff, allowed knowledge, join keys, version identities, and treatment of late corrections.

### Feature Model

A feature is treated as a versioned semantic computation plus input contract, transformation identity, ownership, validation policy, materialization state, and access interface. An online store is not treated as the feature's complete authority. Offline and online paths may share code, intermediate representations, generated transformations, or conformance tests, but parity is demonstrated through evidence rather than assumed from topology.

### Responsibility Model

- **Producer:** source semantics, version/revision notice, correction boundaries, and producer-side recovery evidence.
- **Product/workload:** feature meaning, training intent, acceptance criteria, outcome interpretation, and use-context risk.
- **Platform:** reusable ingestion, validation, transformation, materialization, lineage, quarantine, and recovery mechanisms.
- **Independent authority:** security, privacy, retention, deletion, exception, incident, and release-risk decisions where separation is required.
- **Provider:** only obligations established through service documentation and contract, including availability limits, change notice, data handling, evidence export, support, portability, and termination.

## Evidence Model

### Research Fan-Out

Use three independent research tracks before drafting:

1. **Contracts, identity, and versioning:** semantic contracts, table/snapshot formats, manifests, lineage, and reproducibility.
2. **Temporal correctness and feature systems:** event time, watermarks, late data, point-in-time joins, offline/online feature architecture, and parity.
3. **Governance, reliability, and recovery:** validation, SLIs/SLOs, access, retention, deletion, replay, backfill, quarantine, and incident recovery.

Each track must read at least four authoritative primary or first-party sources in full and write a separate research report. Reports include methodology, exact URLs, publication/update dates, accessed date, applicability limits, conflicts, accepted/rejected candidates, and changelog.

### Initial Source Families to Verify

- Canonical papers on hidden ML technical debt and production-readiness testing.
- Official Apache Kafka and Apache Flink documentation/specifications for event and processing semantics.
- Official Apache Iceberg specification and/or Delta Lake protocol for snapshots, manifests, and table evolution.
- Official Feast documentation for offline/online stores and historical point-in-time feature retrieval, bounded to Feast behavior.
- Primary or first-party sources for feature-store architecture and training-serving skew.
- Official TensorFlow Data Validation or equivalent first-party validation documentation.
- OpenLineage specification and first-party lineage documentation where claims are directly supported.
- NIST AI RMF and NIST SP 800-53 controls already used by the handbook where governance or security claims require them.
- Official cloud documentation only for claims about that provider, not as universal architecture evidence.

Marketing-only, moving, inaccessible, superseded, or non-entailing sources are rejected explicitly. Product behavior is version-pinned with a review deadline.

### Claim Ledger

Chapter 2 claim IDs use `CH02-C001`, `CH02-C002`, and so on. The existing 13-field CSV schema remains unchanged. Chapter 1 rows and statuses remain byte-stable unless a separately reviewed correction is required.

Every quantitative, normative, security, scientific, compatibility, and product/version claim must have a ledger row before prose is drafted. P0/P1 publication claims must be `verified`. Architectural synthesis remains `qualified` and is labeled at point of use.

## Diagram Model

Create four editable Mermaid figures under `diagrams/chapter-02/`:

1. `fig-01-data-lifecycle-time.mmd` — source event through contract, ingestion, transformation, dataset identity, feature materialization, consumption, and feedback.
2. `fig-02-data-feature-authorities.mmd` — data bytes, dataset identities, feature definitions, materializations, validation evidence, lineage, decisions, and derived views.
3. `fig-03-point-in-time-parity.mmd` — event-time cutoff, historical join, offline computation, online computation, conformance evidence, and consumer boundaries.
4. `fig-04-semantic-change-recovery.mmd` — unit change propagation, blind structural checks, temporal contamination, detection, quarantine, replay/backfill, irrecoverable interval, and restored evidence.

Every figure requires the existing ten registry fields, a stable natural ATX anchor, original/adapted provenance, a complete text alternative, and explicit data/control/artifact/telemetry legend. Color and arrow style cannot be the only carriers of meaning.

Before technical approval, render all four sources with a pinned Mermaid CLI into temporary SVG and PNG artifacts, validate SVG XML, and inspect the images for clipping and collisions.

## Editorial Model

Use the Chapter 1 operator voice and evidence labels. Lead major sections with the recurring incident, a contract, a dataset manifest, a feature definition, a failed join, or a recovery decision.

Chapter 2 must include:

- A compact in-chapter linked table of contents.
- Point-of-use links to each diagram source and text alternative.
- Linear-accessible alternatives to dense wide tables.
- Concise forward-boundary paragraphs rather than repeated sentence templates.
- One bounded-synthesis qualifier for a group only when the boundary genuinely applies to the entire group.
- At least 18 interview questions split across Senior, Staff, and Principal scope.
- A question-to-evidence map with must-have signals, applicable dimensions, disqualifying omissions, neutral follow-up guidance, and deterministic role-level scoring caps.
- An architecture decision record (ADR) exercise with explicit or learner-declared cost, volume, staffing, retention, recovery, provider, and reversal assumptions.

The style guide must be extended with a Chapter 2 template and generic multi-chapter diagram-registry language without weakening the publication-ready Chapter 1 contract.

## Validation Design

Extend the validator and its fixture suite through test-driven development.

### Required CLI Behavior

Support chapter-scoped validation without breaking existing commands. The planned interface is:

```text
validate_handbook.sh --profile structure mlops/architect-handbook
validate_handbook.sh --profile release --chapter 1 mlops/architect-handbook
validate_handbook.sh --profile release --chapter 2 mlops/architect-handbook
```

The existing release command without `--chapter` remains backward-compatible and validates every chapter whose release contract is registered.

### Chapter 2 Checks

- Required Chapter 2 file and exact H2 sequence.
- Required four Chapter 2 diagram filenames and unique registry targets.
- `CH02-CNNN` format, sequence, source-key resolution, and no unresolved P0/P1 row.
- Chapter citation and claim-coverage reconciliation.
- ToC links and point-of-use text-alternative links.
- Changelog, fences, headings, markers, placeholders, banned phrases, unsupported superlatives, and generated IDs.
- Preservation of Chapter 1 release validation and its 27-test baseline.

Every validator behavior change requires a failing fixture first, observed RED, minimal GREEN implementation, and full regression run.

## Review and Lifecycle

Chapter 2 uses the existing lifecycle:

```text
Planned -> Researching -> Draft -> Technical Review -> Editorial Review -> Verified -> Publication Ready
```

### Review Gates

1. Independent technical architecture review.
2. Independent evidence and citation-entailment review.
3. Independent editorial and accessibility review.
4. Scoped rereview of every Critical or Important correction.
5. Final whole-milestone release audit.

Chapter 1 remains `Publication Ready` throughout. Chapter 2 status is recorded independently and may not inherit Chapter 1 approval.

## File and Interface Design

### Create

```text
mlops/architect-handbook/chapters/02-data-feature-architecture.md
mlops/architect-handbook/diagrams/chapter-02/README.md
mlops/architect-handbook/diagrams/chapter-02/fig-01-data-lifecycle-time.mmd
mlops/architect-handbook/diagrams/chapter-02/fig-02-data-feature-authorities.mmd
mlops/architect-handbook/diagrams/chapter-02/fig-03-point-in-time-parity.mmd
mlops/architect-handbook/diagrams/chapter-02/fig-04-semantic-change-recovery.mmd
mlops/architect-handbook/sources/research/chapter-02-contracts-identity.md
mlops/architect-handbook/sources/research/chapter-02-temporal-feature-systems.md
mlops/architect-handbook/sources/research/chapter-02-governance-recovery.md
```

### Modify

```text
mlops/architect-handbook/README.md
mlops/architect-handbook/EDITORIAL_STATUS.md
mlops/architect-handbook/STYLE_GUIDE.md
mlops/architect-handbook/GLOSSARY.md
mlops/architect-handbook/CHANGELOG.md
mlops/architect-handbook/sources/references.md
mlops/architect-handbook/sources/claim-ledger.csv
mlops/architect-handbook/scripts/validate_handbook.sh
mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Chapter 2 consumers rely on stable Chapter 1 glossary terms, evidence labels, flow grammar, responsibility vocabulary, and lifecycle states. Chapter 2 may extend these interfaces but may not silently redefine them.

## Acceptance Criteria

- The raw manuscript is untouched and has exact start/end observations.
- Chapter 1 remains publication-ready and passes its release contract after every validator change.
- Chapter 2 contains all 15 required H2 sections plus changelog in exact order.
- Every high-risk claim is verified and every synthesis remains explicitly qualified.
- Research reports meet source-count, methodology, date, applicability, and conflict requirements.
- The recurring scenario is visibly illustrative and contains no invented company evidence.
- Data bytes, metadata identities, decisions, controllers, and observed state remain distinct.
- Point-in-time correctness declares time cutoff, allowed knowledge, identity, keys, and correction policy.
- Parity claims are evidence-backed and do not promise universal equality.
- All four diagrams render, include ten registry fields and text alternatives, and pass semantic review.
- ADR and interview material is decision-complete and role-calibrated.
- Chapter-scoped and all-chapter validator commands pass with zero failures.
- Maintained-content marker, generated-ID, placeholder, banned-phrase, and stale-evidence scans are clean.
- Independent technical, evidence, editorial, and release audits have zero unresolved Critical or Important findings.
- README, status, glossary, bibliography, ledger, diagram registry, and changelogs are synchronized.
- A fresh maintained-file manifest and final verification report are recorded without a Git commit.

## Failure Handling

- If an authoritative source does not entail a planned claim, narrow, qualify, or remove the claim.
- If product documentation cannot be pinned, do not publish its behavior as reproducible version evidence.
- If batch and online computations cannot be shown equivalent, document the allowed divergence and its conformance test.
- If contaminated records cannot be distinguished or normalized, quarantine or discard the interval instead of claiming reconstruction.
- If a diagram renders but misstates authority or direction, technical review remains blocked.
- If the validator passes but a reviewer finds semantic failure, the reviewer finding controls.
- If Chapter 2 validation breaks Chapter 1, restore backward compatibility before drafting continues.
- If the raw manuscript grows, record the new observation and continue without rollback.

## Future Chapter Boundaries

### Handoff to Chapter 3

Chapter 2 produces immutable or versioned dataset references, feature-definition identities, validation evidence, lineage, and recovery state. Chapter 3 consumes those artifacts but owns orchestration, CT, approval, desired deployment state, model release, and rollback.

### Handoff to Chapter 4

Chapter 2 defines feature access contracts, online/offline materialization evidence, freshness and parity signals, and fallback-data boundaries. Chapter 4 consumes those interfaces but owns serving protocols, runtime capacity, inference SLOs, load shedding, autoscaling, and model-serving rollout.

### Later GenAI Milestone

RAG and agentic data architecture will reuse contract, identity, lineage, retention, and recovery principles, but will add corpus/chunk identity, embedding versions, retrieval evaluation, prompt/context evidence, vector-store consistency, and agent-memory boundaries under a separately approved design.

## Changelog

### 2026-08-24

- Created the proposed Chapter 2 design and decomposed the user-approved domains into Chapters 2-4.
- Selected predictive-ML-first and vendor-neutral architecture with bounded implementation examples.
- Defined Chapter 2 sections, recurring scenario, authority/time/feature models, evidence research fan-out, diagrams, validator extension, lifecycle, files, acceptance criteria, and future handoffs.
