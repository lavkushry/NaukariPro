# Chapter 1 Governance and Reliability Research

**Research date:** 2026-08-23  
**Accessed date for every web source:** 2026-08-23  
**Audience:** Senior, Staff, and Principal MLOps / ML Platform Architects  
**Scope:** AI risk governance, operational accountability, lifecycle monitoring, service-level reliability, system-of-record integrity, and directly relevant artifact supply-chain controls.

## Executive finding

A production ML platform needs two linked but non-substitutable control systems. The reliability system measures user-visible service outcomes and drives operational decisions through service-level indicators (SLIs), service-level objectives (SLOs), and error-budget policy. The AI-risk system governs intended use, accountable decision makers, test and evaluation evidence, residual risk, post-deployment monitoring, incident response, change control, and retirement. A healthy latency SLO cannot establish that a model is safe, valid, fair, or being used within its approved context; a completed risk assessment cannot establish that an endpoint is available or a feature pipeline is fresh. This separation is a **handbook synthesis** of the [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1) and Google’s [Implementing SLOs](https://sre.google/workbook/implementing-slos/).

## Methodology

- Searched the live web with official-domain queries for NIST AI RMF 1.0, the NIST AI RMF Playbook, Google SRE SLO guidance, Google Cloud MLOps lifecycle guidance, and SLSA provenance requirements.
- Prioritized standards, government publications, official specifications, and first-party engineering documentation. Search snippets were discovery aids only; no claim below depends on a search-result excerpt.
- Read five authoritative source sets in full: the 48-page AI RMF 1.0 PDF; the 147-page Playbook PDF, including every Govern, Map, Measure, and Manage subcategory; the complete Google SRE Workbook chapter on implementing SLOs; the complete Google Cloud MLOps automation article; and the complete SLSA v1.2 overview plus Build requirements page.
- Cross-checked the Playbook PDF against its landing page and audit log, and checked the NIST AI RMF landing page for revision status as of the access date.
- Paraphrased source claims. Every conclusion is labeled **Sourced fact** or **Handbook synthesis**. No production metric, SLO target, incident rate, or economic benefit was inferred or invented.

## Source register

| Key | Source and exact direct URL | Publication or update date | Review status | Use in this report |
| --- | --- | --- | --- | --- |
| `NIST-AI-RMF-2023` | *Artificial Intelligence Risk Management Framework (AI RMF 1.0)* — <https://doi.org/10.6028/NIST.AI.100-1> (direct PDF: <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf>) | Published 2023-01-26 | Read in full; accepted | Core governance outcomes, lifecycle accountability, monitoring, third-party risk, retirement, and limits of the framework |
| `NIST-AI-RMF-STATUS-2026` | NIST AI RMF program page — <https://www.nist.gov/itl/ai-risk-management-framework> | Page states AI RMF 1.0 is under revision as of access; no page-level update date shown | Read in full; accepted for status only | Establishes that 1.0 remains published but is being revised; prevents presenting 1.0 as temporally final |
| `NIST-AI-RMF-PLAYBOOK` | NIST AI RMF Playbook — <https://airc.nist.gov/airmf-resources/playbook/> (direct PDF: <https://airc.nist.gov/docs/AI_RMF_Playbook.pdf>) | Initial Measure/Manage release 2023-01; audit-log changes 2023-03; PDF added 2023-08. No document revision identifier is exposed | PDF read in full; landing page and audit log read in full; accepted with volatility warning | Optional implementation actions and evidence artifacts, not mandatory controls |
| `NIST-PLAYBOOK-AUDIT` | Playbook Audit Log — <https://airc.nist.gov/airmf-resources/playbook/audit-log/> | Last listed entry 2023-08 | Read in full; accepted for provenance only | Dates the visible Playbook change history and exposes its revision-identification limitation |
| `GOOGLE-SRE-SLO-2018` | *Implementing SLOs*, Google SRE Workbook — <https://sre.google/workbook/implementing-slos/> | Workbook copyright 2018; chapter page has no revision date | Read in full; accepted | User-centric SLIs, error-budget policy, SLO ownership, dependency boundaries, and review practices |
| `GOOGLE-CLOUD-MLOPS-2024` | *MLOps: Continuous delivery and automation pipelines in machine learning* — <https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning> | Last reviewed and updated 2024-08-28 UTC | Read in full; accepted within stated scope | Predictive-ML CI/CD/continuous-training controls, metadata, validation, monitoring, and rollback context |
| `SLSA-1.2` | SLSA v1.2 specification — <https://slsa.dev/spec/v1.2/> and Build requirements — <https://slsa.dev/spec/v1.2/build-requirements> | Version 1.2; pages do not state a publication date; official pages show 2026 copyright | Both pages read in full; accepted within artifact-build scope | Build provenance, digest binding, authenticity, control-plane generation, and build isolation |

## Governance and operational accountability

### Governance is a continuous organizational function

- **Sourced fact:** AI RMF 1.0 is voluntary, rights-preserving, non-sector-specific, and use-case agnostic. It organizes outcomes into Govern, Map, Measure, and Manage; Govern is cross-cutting, and risk management is intended to be continuous across the AI lifecycle. The functions and categories are not a checklist or a required execution order. [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- **Sourced fact:** The framework calls for documented roles and communication lines, executive responsibility for development and deployment risk decisions, an AI-system inventory, periodic review, third-party risk policies, incident practices, and safe decommissioning. [NIST AI RMF 1.0, Govern 1, 2, 4, and 6](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- **Sourced fact:** NIST distinguishes the actors who build or use models from actors who perform independent verification and validation as a sound lifecycle arrangement; test, evaluation, verification, and validation (TEVV) continue into operations through monitoring, incident/error tracking, periodic updates, and recalibration. [NIST AI RMF 1.0, Figure 3 and Appendix A](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- **Handbook synthesis:** A platform should expose governance as an operable control plane, not a policy portal. Its minimum decision artifacts are an inventory entry, intended-use and prohibited-use record, risk owner, technical owner, evidence bundle, approval decision, residual-risk acceptance, deployment identity, monitoring plan, incident record, change history, and retirement decision. NIST supports the need for these outcomes but does not prescribe the database schema or tooling.

### Risk tier determines control depth, not whether controls exist

- **Sourced fact:** NIST treats risk tolerance as contextual and changeable. Higher-impact risks call for more urgent and thorough treatment; systems with unacceptable risk should cease development or deployment safely until risk can be managed. Residual risk should be documented for downstream users. [NIST AI RMF 1.0, Sections 1.2.2–1.2.4](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- **Sourced fact:** The Playbook suggests assigning systems to consistent organizational risk scales, allocating oversight according to risk, defining approval/conditional-approval/disapproval paths, and authorizing responsible actors to modify, limit, bypass, or stop a system. These are optional suggestions, not NIST mandates. [NIST AI RMF Playbook](https://airc.nist.gov/docs/AI_RMF_Playbook.pdf)
- **Handbook synthesis:** A risk tier should select evidence depth, reviewer independence, approval authority, monitoring cadence, rollback/bypass readiness, and retention rules. It should not become a waiver for inventory, ownership, version identity, or incident traceability.

### Accountability must attach to decisions and transitions

- **Sourced fact:** The AI RMF assigns executive leadership responsibility for AI development and deployment risk decisions and expects roles, responsibilities, and communication paths to be documented. Manage includes decisions on whether development or deployment should proceed, prioritized responses, assigned deactivation responsibility, post-deployment monitoring, incident response, recovery, change management, and decommissioning. [NIST AI RMF 1.0, Govern 2.1/2.3 and Manage 1/2/4](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- **Handbook synthesis:** “The ML team owns the model” is too coarse to operate. Each transition needs a named decision owner: accept use case, admit data, approve model evidence, authorize deployment, consume risk, invoke rollback or bypass, communicate an incident, and retire the system. One person may hold several roles in a small organization, but the decisions remain distinguishable and auditable.

## Monitoring and lifecycle controls

### Monitoring covers system behavior, model behavior, context, and impact

- **Sourced fact:** NIST calls for pre-deployment and regular in-operation testing, production monitoring of system behavior and components, tracking of known and emergent risks, feedback and appeal mechanisms, safety/security evaluation, and documented post-deployment response and recovery. [NIST AI RMF 1.0, Measure 1–4 and Manage 4](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- **Sourced fact:** The Playbook suggests comparing pre-deployment and production metrics, watching input/output distribution differences and anomalies, collecting ground truth when available, defining post-alert action, logging out-of-bound use, monitoring third-party and pretrained components, and retaining error, near-miss, change, and version histories. [NIST AI RMF Playbook, Measure 2.4 and Manage 3–4](https://airc.nist.gov/docs/AI_RMF_Playbook.pdf)
- **Sourced fact:** Google Cloud’s predictive-ML guidance adds data/schema validation, model-versus-baseline and segment evaluation, infrastructure/API compatibility testing, canary or A/B validation, pipeline metadata, pointers to prior models, and monitoring that can trigger investigation or retraining. [Google Cloud MLOps guidance](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- **Handbook synthesis:** Monitoring should preserve four separate signal families: service health, pipeline/data health, model behavior, and governance/impact signals. Combining them into one “model health” score hides ownership and response boundaries.

### Retraining is not deployment authorization

- **Sourced fact:** Google Cloud describes triggers for training, automated data and model validation, model registry publication, and progressive environment promotion. Its example includes reviewer approval before pre-production and a manual production promotion after successful pre-production runs. [Google Cloud MLOps guidance, levels 1 and 2](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- **Sourced fact:** NIST Manage 1.1 requires a determination about whether intended purposes and objectives are met and whether development or deployment should proceed. [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- **Handbook synthesis:** A continuous-training trigger may create a candidate. Promotion remains a separate, policy-governed decision. Automation may execute that policy, but it must not silently collapse training success, validation success, risk acceptance, and deployment approval into one event.

### Retirement is part of reliability and governance

- **Sourced fact:** NIST includes safe decommissioning, procedures to supersede/disengage/deactivate systems that violate intended use, post-deployment monitoring, incident response, recovery, and change management. The Playbook further suggests dependency analysis, retention for forensic/legal review, redeployment criteria, and tracking downstream effects. [NIST AI RMF 1.0, Govern 1.7 and Manage 2.4/4.1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) and [Playbook](https://airc.nist.gov/docs/AI_RMF_Playbook.pdf)
- **Handbook synthesis:** An architecture is incomplete if it can deploy but cannot identify dependents, bypass or roll back safely, preserve decision evidence, and retire the model, endpoint, features, and scheduled training jobs coherently.

## Reliability and SLO boundaries

### Begin at the user journey, then allocate component objectives

- **Sourced fact:** Google defines an SLI as a service-level measurement and an SLO as a target reliability level. Its implementation guidance prioritizes user-centric whole-stack outcomes and identifies availability, latency, quality, pipeline freshness, pipeline correctness, pipeline coverage, and storage durability as candidate SLI types. [Google SRE, Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- **Sourced fact:** Google recommends a small set of critical SLI types, documents the measurement implementation and its blind spots, and warns that dependency calculations can be misleading when components share control planes or failure domains. Critical dependencies need owned objectives compatible with the dependent user journey. [Google SRE, worked example and dependency modeling](https://sre.google/workbook/implementing-slos/)
- **Handbook synthesis:** For online inference, a user-journey SLO may depend on endpoint availability/latency plus outcome quality. For batch or streaming ML, freshness, coverage, and correctness can be closer to user impact than job success. Component objectives are diagnostic and contractual boundaries; they do not replace the end-to-end objective.

### Error budgets are decision policy, not dashboard decoration

- **Sourced fact:** Google’s approach requires stakeholder-approved SLOs, an owner empowered to trade feature velocity against reliability, a written error-budget policy, and a refinement process. A policy may prioritize reliability work or freeze changes when the budget is exhausted; the document should record authors, reviewers, approvers, review date, measurement method, rationale, response actions, and escalation path. [Google SRE, Getting Started and Establishing an Error Budget Policy](https://sre.google/workbook/implementing-slos/)
- **Handbook synthesis:** An ML platform should connect budget consumption to deploy controls through an explicit policy. Whether model-quality or risk signals participate in that policy depends on the use case; the SRE source does not prescribe AI-specific error budgets.

### Reliability, model quality, and trustworthiness remain distinct

- **Sourced fact:** NIST treats validity/reliability, safety, security/resilience, accountability/transparency, explainability/interpretability, privacy, and fairness as interacting trustworthiness characteristics. It warns that addressing one characteristic does not establish the others. [NIST AI RMF 1.0, Section 3](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf)
- **Handbook synthesis:** Keep three decision layers visible: service SLOs answer whether the delivery system met a user-facing reliability promise; model acceptance criteria answer whether a candidate met bounded technical and product requirements; risk controls answer whether the system may operate in the intended context. A single green dashboard cannot entail all three.

## System-of-record integrity and supply-chain controls

### Canonical records need linked identities

- **Sourced fact:** Google Cloud’s MLOps metadata example records pipeline/component versions, execution times and actor, parameters, produced artifacts, prior-model pointers, and evaluation metrics to support lineage, reproducibility, comparison, debugging, and rollback. [Google Cloud MLOps guidance, Metadata management](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- **Sourced fact:** NIST’s transparency and accountability treatment spans design decisions, training data, model training, intended use, deployment, post-deployment decisions, and the actors who made them. The Playbook suggests inventories, audit logs, data provenance, deployment/change histories, and secure repositories for evidence. [NIST AI RMF 1.0, Section 3.4](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) and [Playbook](https://airc.nist.gov/docs/AI_RMF_Playbook.pdf)
- **Handbook synthesis:** Each fact class should have one canonical system of record and stable identifiers, while dashboards and catalogs remain derived views. A deployment record should link immutable or versioned identities for source, training/evaluation data references, feature definitions, pipeline, environment, model artifact, evaluation bundle, risk decision, approver, runtime configuration, and rollback target. The sources support traceability outcomes but do not mandate this exact schema.

### Build provenance secures a narrower boundary than ML lineage

- **Sourced fact:** SLSA v1.2 Build requires provenance that identifies an output package by cryptographic digest and describes how it was produced. Higher levels add verifiable authenticity, control-plane-generated provenance resistant to tenant tampering, hosted builds, and build isolation. [SLSA v1.2 Build requirements](https://slsa.dev/spec/v1.2/build-requirements)
- **Sourced fact:** SLSA explicitly scopes the Build track to software package production and separates producer responsibilities from build-platform responsibilities. It also allows resolved-dependency provenance to be incomplete. [SLSA v1.2](https://slsa.dev/spec/v1.2/) and [Build requirements](https://slsa.dev/spec/v1.2/build-requirements)
- **Handbook synthesis:** Apply SLSA directly to pipeline packages, serving binaries, containers, and packaged model artifacts when they fit the specification’s artifact model. Do not claim that a SLSA level proves dataset suitability, model validity, approval legitimacy, or complete ML lineage. Those require linked data/model/governance records and independent controls.

### Third-party ML components need both provenance and operational contingency

- **Sourced fact:** NIST Govern 6 and Manage 3 call for policies, monitoring, controls, and contingency processes for third-party data, software, AI systems, and pretrained models. [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- **Handbook synthesis:** Procurement evidence, license/usage constraints, vulnerability and change notification, version pinning, integrity verification, evaluation in the local context, fallback behavior, and exit/decommission plans belong to one third-party control chain. Provenance answers where an artifact came from; it does not answer whether the organization should use it.

## Control model for Chapter 1 synthesis

| Decision boundary | Minimum evidence | Named decision | Runtime consequence |
| --- | --- | --- | --- |
| Use-case intake | Intended context, affected parties, non-AI alternative, risk tolerance | Proceed, narrow, or reject | Inventory entry and control tier |
| Candidate admission | Versioned lineage references, validation results, known limits | Accept for evaluation or reject | Candidate becomes eligible for promotion only |
| Production promotion | Service tests, model acceptance evidence, risk decision, rollback target | Approve, conditionally approve, or reject | Deployment identity and monitoring plan activated |
| In-operation review | SLO state, pipeline/data signals, model/impact signals, incidents, feedback | Continue, constrain, retrain, rollback, bypass, or stop | Change record and accountable action |
| Retirement | Dependents, retention duties, replacement/fallback, residual risk | Retire or extend under conditions | Endpoint, pipeline, features, and schedules deactivated coherently |

**Handbook synthesis:** The table is an original architecture pattern derived from the cited NIST, Google, and SLSA controls. It is not a quoted standard, and the evidence depth and approval authority must be calibrated to the deployment context and applicable law.

## Applicability limits

- AI RMF 1.0 and the Playbook are voluntary and outcome-focused. They do not substitute for sector law, regulation, contractual duties, or domain safety standards. [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1)
- The NIST landing page says AI RMF 1.0 is being revised, and the Playbook says it will be updated after that revision. Chapter 1 should version-pin claims to 1.0 and repeat the source review before publication and when NIST announces a revision. [NIST status page](https://www.nist.gov/itl/ai-risk-management-framework) and [Playbook landing page](https://airc.nist.gov/airmf-resources/playbook/)
- Google’s SLO guidance is practitioner guidance from Google, not a regulatory standard. Its example thresholds and review cadences are examples, not universal targets. [Google SRE](https://sre.google/workbook/implementing-slos/)
- Google Cloud’s MLOps article states that it applies primarily to predictive AI systems. Generative and agentic systems require additional evaluation, safety, and interaction controls not established by that source. [Google Cloud MLOps guidance](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- SLSA v1.2 Build addresses artifact-production integrity. It does not certify model behavior, data rights, data representativeness, or AI risk acceptance. [SLSA v1.2 Build requirements](https://slsa.dev/spec/v1.2/build-requirements)
- NIST does not prescribe a specific model registry, metadata database, approval engine, SLO product, or ownership matrix. Concrete tool choices in Chapter 1 must be labeled architecture examples or later-chapter decisions.

## Source candidates accepted and rejected

### Accepted

- **NIST AI RMF 1.0:** accepted as the primary cross-sector governance framework because it directly defines lifecycle risk outcomes, accountability, monitoring, third-party risk, and decommissioning. Version-pin to 1.0 because revision is in progress.
- **Current NIST AI RMF Playbook:** accepted for concrete implementation options and evidence questions. Treat every action as voluntary and selectable; do not convert the Playbook into a compliance checklist.
- **Google SRE Workbook, Implementing SLOs:** accepted for reliability practice, user-centric SLI design, ownership, error-budget decisions, and dependency reasoning. Do not generalize its examples into required targets.
- **Google Cloud MLOps continuous-delivery article:** accepted for predictive-ML lifecycle and metadata examples. Constrain claims to its stated predictive-AI scope and to Google’s documented pattern.
- **SLSA v1.2 Build requirements:** accepted for software/artifact supply-chain integrity. Constrain its role to build provenance and isolation; connect rather than equate it with ML lineage.

### Rejected or deferred

- **SLSA v1.1:** rejected because v1.2 is the approved version exposed by the official specification site on the access date.
- **NIST SP 800-218 SSDF 1.1:** reviewed as an official candidate at <https://csrc.nist.gov/pubs/sp/800/218/final> and deferred from central Chapter 1 claims. It is broad secure-software-development guidance, while SLSA v1.2 more directly supports the narrow artifact-provenance boundary needed here. SSDF remains suitable for a later secure-development chapter.
- **NIST AI RMF Generative AI Profile (NIST AI 600-1):** deferred because Chapter 1 establishes cross-cutting architecture foundations; the profile’s generative-AI-specific risks belong in a dedicated GenAI/LLMOps treatment. The official NIST program page records its 2024-07-26 release: <https://www.nist.gov/itl/ai-risk-management-framework>.
- **Vendor claims that a registry, monitoring product, or managed AI service creates “governance” by itself:** rejected as unable to support a system-level accountability claim. Product documentation can establish product behavior only and must be version-pinned in later tool-selection work.
- **Unattributed blogs and search summaries:** rejected because they cannot carry normative, security, safety, or version-sensitive Chapter 1 claims.

## Unresolved conflicts and research gaps

- **Revision conflict:** AI RMF 1.0 is the published framework, but NIST states it is under revision. The current Playbook is aligned to 1.0 and will be updated afterward. Resolution: cite 1.0 explicitly, record the access date, and keep Chapter 1 below `Verified` until a pre-publication freshness review confirms whether the revision has landed. [NIST status page](https://www.nist.gov/itl/ai-risk-management-framework)
- **Playbook version ambiguity:** the audit log’s last visible entry is August 2023, while the Playbook is described as living and the download lacks a visible revision identifier. Resolution: cite both the stable landing page and direct PDF, record access date, and treat action-level content as volatile. [Playbook audit log](https://airc.nist.gov/airmf-resources/playbook/audit-log/)
- **SLO-to-risk coupling:** neither NIST nor Google defines a universal formula for translating AI harm, quality degradation, or drift into an error budget. Resolution: present any coupling as a use-case-specific architecture decision, not a sourced standard.
- **Delayed ground truth:** the sources recognize ongoing measurement but do not supply one architecture for labels that arrive late, are sparse, or do not arrive. Chapter 1 should state the gap and avoid presenting proxy drift metrics as proof of outcome quality.
- **Shared system-of-record schema:** the sources require or recommend traceability outcomes but do not define a common enterprise schema spanning data, model, deployment, risk, and incident records. The proposed linked-identity pattern is synthesis and needs technical review.
- **Legal applicability:** this report does not determine which laws or sector rules apply to a deployment. That analysis requires jurisdiction, domain, affected parties, data categories, and intended use.

## Chapter 1 claims ready for synthesis

1. **Sourced fact:** AI governance is continuous and cross-cutting across the lifecycle; it includes explicit roles, inventories, measurement, response, third-party controls, and retirement. [`NIST-AI-RMF-2023`](https://doi.org/10.6028/NIST.AI.100-1)
2. **Handbook synthesis:** Reliability and AI risk are coupled control systems with separate evidence and decision semantics; neither substitutes for the other.
3. **Sourced fact:** User-centric SLOs and a stakeholder-approved error-budget policy turn reliability measurements into prioritization and change decisions. [`GOOGLE-SRE-SLO-2018`](https://sre.google/workbook/implementing-slos/)
4. **Handbook synthesis:** Continuous training produces a candidate; a separate policy-governed promotion decision authorizes production use.
5. **Sourced fact:** Predictive-ML operations require validation and monitoring of code, data, models, pipelines, serving behavior, metadata, and production performance. [`GOOGLE-CLOUD-MLOPS-2024`](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
6. **Handbook synthesis:** One canonical record per fact class, joined by immutable/versioned identities, is the practical boundary for auditability and recovery.
7. **Sourced fact:** SLSA Build provenance can bind a software artifact digest to how it was produced and, at higher levels, to authenticated and isolated build infrastructure. [`SLSA-1.2`](https://slsa.dev/spec/v1.2/build-requirements)
8. **Handbook synthesis:** Build provenance is one link in ML supply-chain integrity; it does not establish data fitness, model quality, or deployment approval.

## Changelog

### 2026-08-23

- Reworded an ordinary verb that collided with the case-insensitive unresolved-marker scan without changing the evidence claim.
- Normalized first-use SLI and SLO expansions to the controlled glossary spellings after Task 4 review.
- Created the Chapter 1 governance and reliability research report.
- Fully reviewed the AI RMF 1.0, current Playbook, Google SRE SLO chapter, Google Cloud predictive-MLOps article, and SLSA v1.2 overview and Build requirements.
- Added fact-versus-synthesis labels, exact URLs and dates, source acceptance decisions, applicability limits, revision conflicts, and unresolved evidence gaps.
