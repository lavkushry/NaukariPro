# Chapter 1 Platform Strategy Research

**Research date:** 2026-08-23  
**Accessed date for every web source:** 2026-08-23  
**Scope:** Platform and product-team ownership, automation maturity, build-versus-buy, managed-versus-self-hosted choices, and Senior/Staff/Principal decision scope  
**Evidence posture:** Primary or authoritative sources for factual claims; cross-source architectural judgments labeled as handbook synthesis

## Table of contents

1. [Methodology](#methodology)
2. [Source register](#source-register)
3. [Evidence findings](#evidence-findings)
4. [Platform and product-team responsibility model](#platform-and-product-team-responsibility-model)
5. [Build, buy, managed-service, and self-hosted decisions](#build-buy-managed-service-and-self-hosted-decisions)
6. [Senior, Staff, and Principal decision scope](#senior-staff-and-principal-decision-scope)
7. [Applicability limits](#applicability-limits)
8. [Unresolved conflicts and bounded resolutions](#unresolved-conflicts-and-bounded-resolutions)
9. [Accepted and rejected source candidates](#accepted-and-rejected-source-candidates)
10. [Chapter 1 drafting guidance](#chapter-1-drafting-guidance)
11. [Changelog](#changelog)

## Methodology

The research answered four questions:

1. Which system capabilities distinguish manual ML delivery from pipeline and continuous integration/continuous delivery (CI/CD) automation?
2. Which responsibilities belong with a reusable platform, a workload or product team, and an underlying capability provider?
3. Which constraints should govern build, buy, managed-service, and self-hosted decisions?
4. How should the decision scope change from Senior to Staff to Principal without implying unsupported organizational scale?

Searches were restricted to first-party cloud architecture documentation, Cloud Native Computing Foundation (CNCF) working-group material, and the Team Topologies authors' site. Nine key pages were read in full. Search snippets were discovery aids only; no claim below relies on a snippet. Vendor guidance is treated as authoritative for the vendor's stated design model, not as neutral proof that its service is cheaper or more reliable in every workload.

Each finding carries one of these labels:

- **Sourced fact:** A close paraphrase entailed by the linked source.
- **Handbook synthesis:** A decision rule derived from multiple cited sources and explicit assumptions.
- **Source-position claim:** What a vendor or organization recommends; it is not asserted as a universal outcome.

No quantitative performance, cost, productivity, or adoption claim was accepted. The report records source dates where the publisher exposes them and records `date not stated` where it does not.

## Source register

| Key | Source and exact direct URL | Publisher | Publication or update date | Read status | Primary use and limit |
| --- | --- | --- | --- | --- | --- |
| `PS-GCP-MLOPS-2024` | *MLOps: Continuous delivery and automation pipelines in machine learning* — <https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning> | Google Cloud Architecture Center | Last reviewed and updated 2024-08-28 | Read in full | Defines predictive-ML automation levels and required pipeline capabilities. Google explicitly scopes the document primarily to predictive AI. |
| `PS-AWS-ML-LENS-2025` | *Machine Learning Lens* — <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html> | Amazon Web Services | Publication date 2025-11-19 | Read in full | Establishes the lens audience, scope, and distinction from the Generative AI Lens. AWS-specific implementation advice is not vendor-neutral evidence. |
| `PS-AWS-DESIGN-2025` | *Well-Architected machine learning design principles* — <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/design-principles.html> | Amazon Web Services | Part of the 2025-11-19 Machine Learning Lens; page-specific date not stated | Read in full | Supports ownership, protection, resiliency, reusability, reproducibility, automation, resource analysis, and continuous improvement. |
| `PS-AWS-BUILD-BUY-2025` | *MLCOST02-BP02 Perform a tradeoff analysis between custom and pre-trained models* — <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost02-bp02.html> | Amazon Web Services | Part of the 2025-11-19 Machine Learning Lens; page-specific date not stated | Read in full | Supplies a requirements and total-cost comparison frame. Product recommendations apply to AWS and require independent workload validation. |
| `PS-AWS-MANAGED-2025` | *MLCOST01-BP02 Use managed services to reduce total cost of ownership (TCO)* — <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost01-bp02.html> | Amazon Web Services | Part of the 2025-11-19 Machine Learning Lens; page-specific date not stated | Read in full | Identifies infrastructure, personnel, maintenance, scaling, upgrades, utilization, and pricing model as cost inputs. Its comparative cost conclusion is not adopted without a disclosed workload model. |
| `PS-AZURE-AI-2026` | *AI workloads on Azure* — <https://learn.microsoft.com/en-us/azure/well-architected/ai/get-started> | Microsoft | Last updated 2026-05-07 | Read in full | Frames SaaS, platform as a service (PaaS), and custom choices using data control, customization, upkeep, performance, expertise, security, and compliance. Excludes low-code/no-code and high-performance-computing workloads. |
| `PS-AZURE-WORKLOADS-2025` | *Azure Well-Architected Framework workloads* — <https://learn.microsoft.com/en-us/azure/well-architected/workloads> | Microsoft | Last updated 2025-08-12 | Read in full | Defines workload-team and centralized-team responsibilities, shared obligations, constraints, service expectations, budget, and change communication. Azure implementation examples are optional, not required for the responsibility model. |
| `PS-CNCF-PLATFORMS-2023` | *CNCF Platforms White Paper* — <https://tag-app-delivery.cncf.io/whitepapers/platforms/>; version record — <https://github.com/cncf/tag-app-delivery/blob/main/platforms-whitepaper/README.md> | CNCF TAG App Delivery Platforms Working Group | Version 1 completed March 2023; web edition is maintained | Read in full | Supports platform-as-product, self-service, optional and composable capabilities, user research, capability-provider boundaries, and a thin integration layer. Written for cloud-native application delivery, so ML-specific extensions are synthesis. |
| `PS-TT-TVP-2019` | *What is a Thinnest Viable Platform (TVP)?* — <https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp> | Team Topologies authors | Published 2019-11-07; modified 2024-06-01 | Read in full | First-party explanation of keeping a platform no thicker than necessary; its wiki-page example; developer experience; and platform-as-product. It is practitioner guidance rather than a standard. |

## Evidence findings

### Automation maturity describes delivery capability, not organizational prestige

**Sourced fact:** Google separates manual ML delivery, automated ML pipelines, and automated CI/CD for pipeline changes. Pipeline automation adds validation, triggers, metadata, reusable components, and recurrent execution; CI/CD automation adds build, test, deployment, registry, orchestration, and monitoring stages. The same source states that a manual process can be sufficient where models change or retrain infrequently and recommends gradual adoption rather than an immediate jump between levels. [Google Cloud automation guidance](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)

**Sourced fact:** In Google's model, ML continuous integration tests more than source code: it also validates data, schemas, models, component outputs, and pipeline integration. Continuous delivery concerns both pipeline implementations and the prediction service they produce, while continuous training covers retraining and serving. [Google Cloud automation guidance](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)

**Sourced fact:** AWS's design principles join ownership and automation with protection, recoverability, reusability, reproducibility, resource trade-off analysis, cost awareness, and continuous improvement. [AWS ML design principles](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/design-principles.html)

**Handbook synthesis:** Automation is one capability in a workload design; it does not by itself establish governance or reliability. **Assumption:** An automated pipeline can exist without documented accountability, risk decisions, user-journey service objectives, incident and recovery ownership, or retirement controls described in the sibling [Chapter 1 governance and reliability research](chapter-01-governance-reliability.md). This inference therefore treats automation evidence and governance or reliability evidence as separate.

**Handbook synthesis:** Chapter 1 should use the Google levels as an automation-capability diagnostic. It should not turn them into a universal enterprise-maturity score. The decision question is: which manual transition creates unacceptable release, traceability, recovery, or operational risk for this workload's change frequency and criticality?

### A platform is a product interface over reusable capabilities

**Sourced fact:** The CNCF paper defines a cloud-native platform as an integrated collection of capabilities presented around user needs. It emphasizes consistent interfaces, self-service, documentation and onboarding, optional composition, secure defaults, and reduced cognitive load. It also says the capability implementation may belong to a managed provider or another internal team while the platform team owns the interface and experience. [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)

**Sourced fact:** CNCF assigns the platform team responsibility for user research, roadmap planning, and interfaces such as portals, application programming interfaces (APIs), documentation, templates, and command-line tools. It recommends focusing platform investment on common requirements and relying on external or internal capability providers where appropriate. [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)

**Sourced fact:** Team Topologies advises keeping a thinnest viable platform no thicker than necessary and says that in a constrained environment it can be a wiki page naming an approved cloud provider and services plus usage guidance. The authors pair thinness with attention to developer experience and stream-aligned teams as customers. [Team Topologies TVP explanation](https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp)

**Handbook synthesis:** An ML platform should begin as a contract, not a tool catalog. The contract names supported journeys, interfaces, service expectations, guardrails, telemetry, escalation paths, and the boundary between platform operation and workload operation. Implementation can combine managed services, open-source components, and custom adapters without exposing every provider detail to users.

### Workload outcome ownership remains with the product team

**Sourced fact:** Microsoft defines a workload as application resources, custom code, AI models, data, and supporting infrastructure that achieve a business outcome. The workload team focuses on that outcome; centralized teams provide shared services, guidance, and guardrails across workloads. [Azure workload guidance](https://learn.microsoft.com/en-us/azure/well-architected/workloads)

**Sourced fact:** Microsoft says the direct workload team handles most requirements, some responsibilities are joint, and some implementation choices can be exclusively centralized. It requires organizations to map responsibilities based on topology, workload type, and criticality rather than assuming the guidance assigns each action to a named job title. [Azure workload guidance](https://learn.microsoft.com/en-us/azure/well-architected/workloads)

**Sourced fact:** Shared-responsibility conversations should make constraints and service expectations explicit, including compliance, networking, observability, performance, service objectives, technical support, budgets, and change control. Outsourcing a component does not remove the workload team's obligation to deliver its outcome. [Azure workload guidance](https://learn.microsoft.com/en-us/azure/well-architected/workloads)

**Handbook synthesis:** A central platform can own a safe delivery path without owning the product's prediction policy, business acceptance criteria, or user harm. Product teams consume platform guarantees and retain accountability for the workload behavior they release.

## Platform and product-team responsibility model

The following is **handbook synthesis** from the [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/), [Azure workload guidance](https://learn.microsoft.com/en-us/azure/well-architected/workloads), [Google Cloud automation guidance](https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning), and [AWS ML design principles](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/design-principles.html). It is a starting point for a responsibility assignment matrix, not a universal organization chart.

| Boundary | Platform team accountable for | Product or workload team accountable for | Shared decision or required handshake |
| --- | --- | --- | --- |
| User journey | Supported golden paths, interfaces, documentation, onboarding, deprecation policy, and feedback loop | Selecting an appropriate supported path or documenting an exception | Adoption criteria, exception duration, and migration plan |
| Infrastructure and runtime | Reusable provisioning contract, provider integration, default isolation, baseline telemetry, and platform service objectives | Workload sizing inputs, runtime-specific configuration, load profile, and application failure behavior | Capacity limits, cost allocation, region constraints, and support hours |
| ML pipeline | Reusable orchestration, artifact interfaces, validation hooks, execution metadata, and deployment mechanisms | Feature logic, training code, evaluation policy, candidate selection, and workload-specific release thresholds | Required gates, override authority, rollback trigger, and evidence retained |
| Security and governance | Organization guardrails, identity integration, policy enforcement points, audit export, and approved capability catalog | Data classification, lawful-use inputs, model and dependency risk assessment, and adherence within the workload | Control ownership, exception approval, incident coordination, and audit evidence |
| Reliability and operations | Platform telemetry, dependency status, platform runbooks, recovery objectives, and breaking-change communication | End-to-end workload service objectives, application telemetry, workload runbooks, and user-impact response | Alert routing, incident command, dependency failure behavior, and recovery testing |
| Product outcome | Platform adoption and capability health signals | Business objective, user experience, model behavior, acceptance criteria, and outcome measurement | Whether a platform limitation changes or blocks the workload requirement |

**Failure boundary:** If the model endpoint is healthy but predictions violate the product's acceptance policy, the product team owns the decision to stop or roll back the workload. If the shared deployment API violates its published contract, the platform team owns restoration of that capability. If a managed provider is causal, the internal owners still coordinate impact, workaround, escalation, and user communication according to the mapped obligations.

**Handbook synthesis - provider contract boundary:** For a managed capability, document the provider-operated service boundary and limits, support and incident-escalation interfaces, change communication, exposed observability and audit interfaces, and export and exit duties. This bounded recommendation combines AWS's managed-service operating-boundary and lifecycle inputs, Microsoft's explicit shared-responsibility discussion topics, and CNCF's capability-provider and thin-interface model. It applies only where actual service documentation and contract terms directly establish each obligation; it does not claim that every provider offers them or transfer workload-outcome accountability. [AWS managed-service guidance](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost01-bp02.html) [Azure workload guidance](https://learn.microsoft.com/en-us/azure/well-architected/workloads) [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)

## Build, buy, managed-service, and self-hosted decisions

### What the official sources support

**Source-position claim:** Microsoft advises evaluating fully managed software as a service (SaaS), PaaS, and custom solutions using business needs, data control, customization, upkeep, performance, expertise, security, and compliance. Its AI workload overview says prebuilt options can fit generic tasks, while business-specific data or compliance constraints can push toward custom work. [Azure AI workload guidance](https://learn.microsoft.com/en-us/azure/well-architected/ai/get-started)

**Source-position claim:** AWS recommends comparing custom and pre-trained models using data availability, task specificity, performance requirements, expertise, development time, infrastructure, security, and long-term maintenance. It also identifies fine-tuning or transfer learning as intermediate choices rather than forcing a binary decision. [AWS custom-versus-pre-trained guidance](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost02-bp02.html)

**Source-position claim:** AWS favors managed services and asks architects to include infrastructure, operational personnel, maintenance, scaling, upgrades, workload utilization, and pricing commitments in total cost of ownership. The page's claim that AWS managed ML has lower total cost than self-managed AWS options is vendor guidance; the page does not expose a reproducible workload model, so this report does not generalize that conclusion. [AWS managed-service cost guidance](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost01-bp02.html)

**Sourced fact:** CNCF recommends a thin platform layer over internal or external capability providers, while keeping platform offerings optional and composable so teams can operate a missing specialized capability themselves. It prioritizes common, undifferentiated capabilities over one-team features. [CNCF Platforms White Paper](https://tag-app-delivery.cncf.io/whitepapers/platforms/)

### Decision sequence

The following sequence is **handbook synthesis**. Apply it per capability, not once for the entire platform.

1. **State the outcome and acceptance envelope.** Record functional need, data sensitivity, regulatory and residency constraints, latency and throughput profile, availability and recovery objectives, integration surfaces, and evidence required for release.
2. **Classify differentiation.** Treat an ordinary capability such as artifact storage or job scheduling differently from proprietary decision logic or a workload-specific control boundary. A capability can be common in one organization and differentiating in another.
3. **Evaluate four implementation modes.** Compare external SaaS/API, managed cloud service, self-hosted third-party software, and custom implementation. Hybrid composition is valid.
4. **Model full lifecycle burden.** Include acquisition, integration, identity and network controls, migration, upgrades, patching, on-call, incident handling, capacity engineering, observability, audit evidence, data movement, support, training, and retirement.
5. **Test control and exit.** Document data ownership, artifact and metadata export, interface portability, retraining or replay feasibility, contractual support, failure isolation, and a credible replacement path.
6. **Prototype the riskiest assumption.** Use representative data and operational constraints to test the requirement that most affects the decision. Avoid using a feature checklist as proof of workload fitness.
7. **Record the decision.** An architecture decision record should name the owner, assumptions, accepted trade-offs, rejected options, evidence, review trigger, and sunset or reconsideration condition.

### Mode comparison

| Mode | Select when evidence shows | Costs and risks to expose | Required exit evidence |
| --- | --- | --- | --- |
| External SaaS or model API | The capability is not differentiating, service behavior fits the workload, and contractual controls satisfy the risk envelope | Provider concentration, opaque implementation, data handling, unit economics, quotas, regional availability, and provider change | Exportable data and logs, substitutable interface, fallback behavior, and contract termination plan |
| Managed cloud service | The service removes operational work while meeting integration, reliability, governance, and cost requirements | Cloud coupling, service limits, shared-responsibility gaps, pricing model, region constraints, and constrained customization | Artifact and metadata export, infrastructure replacement path, dependency inventory, and tested restore or redeploy procedure |
| Self-hosted third-party software | Control, portability, extension, or deployment constraints justify owning operations | Upgrade and patch burden, specialized staffing, scaling, security response, compatibility, and on-call load | Reproducible deployment, versioned configuration, backup and restore, upgrade path, and support contingency |
| Custom implementation | The capability is materially differentiating or no available option meets a documented hard requirement | Product roadmap burden, reliability engineering, security ownership, opportunity cost, adoption, and long-term maintenance | Stable interface, component boundaries, maintained documentation, succession plan, and retirement strategy |

**Decision:** Prefer the thinnest composition that satisfies measured workload requirements and preserves accountable ownership.

**Assumptions:** The organization has identified the workload outcome, control requirements, owners, and lifecycle cost categories. The decision is reviewed when those assumptions change.

**Trade-off:** A thinner managed composition can reduce internal operations but increase provider dependency; a thicker self-hosted or custom composition can increase control but transfers lifecycle and incident obligations to internal teams.

## Senior, Staff, and Principal decision scope

This section is **handbook synthesis**. The levels describe decision horizon and organizational reach, not team size or title equivalence across employers.

| Scope | Decision focus | Evidence expected | Failure to avoid |
| --- | --- | --- | --- |
| Senior | One workload or platform capability: interface, pipeline gate, rollout, runbook, service objective, and operational readiness | Representative tests, dependency contract, cost inputs, security review, rollback proof, and an architecture decision record | Shipping a locally functional component that has no support boundary, telemetry, or recovery path |
| Staff | A cross-team platform journey or capability portfolio: reusable contract, exception model, provider comparison, migration, deprecation, and shared operations | Multiple workload requirements, adoption and support evidence, cross-team responsibility map, reliability and cost trade-offs, and provider exit analysis | Standardizing a local preference that shifts cognitive or operational burden onto many teams |
| Principal | Enterprise platform boundaries and multi-year evolution: investment allocation, operating model, systemic risk, vendor concentration, governance interfaces, and portfolio retirement | Strategic constraints, scenario analysis, organization-wide dependency and risk view, funding and capability model, transition states, and decision-review cadence | Optimizing one platform layer while creating enterprise lock-in, fragmented accountability, or an unfunded operating obligation |

## Applicability limits

- Google labels its automation article as primarily applicable to predictive AI. Its level model does not fully cover foundation-model evaluation, prompt and retrieval changes, agent tool permissions, or provider model-version changes.
- AWS states that its Machine Learning Lens covers broad ML workloads and distinguishes those from its Generative AI Lens. Generative AI design should therefore consult the separate lens before reusing predictive-ML controls unchanged.
- Azure's AI overview excludes low-code/no-code and high-performance-computing workloads. Its build-versus-buy examples concern models and AI services, so this report extends the factors to platform capabilities only as synthesis.
- CNCF's paper addresses cloud-native application delivery. Applying its platform interfaces to feature stores, registries, training pipelines, and inference services requires ML-specific control and lifecycle design.
- Team Topologies material is an organizational design heuristic, not a compliance, reliability, or cost standard.
- A managed service changes the operating boundary; it does not remove internal responsibility for workload outcomes, integration, monitoring, security configuration, incident coordination, or exit planning.
- No source establishes a universally optimal team topology or implementation mode. Workload criticality, regulation, data location, existing skills, provider contracts, and portfolio economics can reverse a local decision.

## Unresolved conflicts and bounded resolutions

### Managed-service cost claims

**Conflict:** AWS presents managed ML services as lowering total cost compared with self-managed AWS options, while the page does not provide a reproducible workload profile or cost calculation. CNCF recommends relying on providers where appropriate but also requires optionality and composability. Azure frames the choice as requirement-dependent.

**Bounded resolution:** Retain AWS's list of cost inputs and operational burdens, but reject the comparative result as a general claim. Chapter 1 should require a workload-specific total-cost model and sensitivity analysis rather than state that one mode costs less.

### Platform operation versus end-to-end product ownership

**Conflict:** CNCF says platform users should not operate services offered by the platform. Microsoft says workload teams remain responsible for workload delivery even when components are outsourced.

**Bounded resolution:** Separate the platform capability from the product workload. The platform or capability provider operates the offered service to its contract; the product team operates the end-to-end workload behavior and coordinates dependency failures. A responsibility map must name incident command, communications, and recovery authority.

### Automation level as a target

**Conflict:** Google's higher levels add automation needed for frequent pipeline changes, yet the same source permits a manual process for infrequently changed models and supports gradual adoption.

**Bounded resolution:** Treat automation as a response to change rate and risk. The target is an acceptable control and recovery posture, not the highest numbered level.

### Custom work for compliance

**Conflict:** Azure suggests business-specific data or compliance requirements can favor custom models, while managed services may also provide relevant controls. The source does not establish that custom implementation is inherently compliant.

**Bounded resolution:** Treat compliance as a set of testable requirements. Choose the mode whose control evidence, contractual terms, data paths, and operating model satisfy those requirements; do not use `custom` or `managed` as a proxy for compliance.

## Accepted and rejected source candidates

| Candidate | Decision | Reason |
| --- | --- | --- |
| Google Cloud MLOps automation guidance | ✅ Accepted | Official architecture guidance directly supports automation-capability and incremental-adoption claims; predictive-AI scope is explicit. |
| AWS Well-Architected Machine Learning Lens | ✅ Accepted with vendor boundary | Official framework supports ownership, automation, lifecycle trade-offs, and evaluation criteria. AWS service outcomes are not generalized. |
| Microsoft Azure Well-Architected AI and workload guidance | ✅ Accepted with scope limits | Official framework directly addresses AI implementation modes and centralized/workload shared responsibility. Azure examples are separated from the cloud-agnostic synthesis. |
| CNCF Platforms White Paper | ✅ Accepted | Working-group publication directly supports platform-as-product, thin integration, self-service, composability, and capability-provider boundaries. Version provenance is available. |
| Team Topologies thinnest viable platform page | ✅ Accepted as practitioner authority | It is a first-party explanation from the framework's authors and directly supports the TVP concept; it is not treated as a standard. |
| AWS three-year lower-TCO comparison for SageMaker AI | ❌ Rejected as a quantitative conclusion | The documentation page exposes no reproducible workload assumptions, cost inputs, or calculation. Only the qualitative cost categories are retained. |
| Kubernetes control-plane documentation | ❌ Rejected for this report | It is authoritative for Kubernetes component behavior but does not support organizational ownership or ML platform sourcing decisions. It belongs in architecture-plane research. |
| MLflow tracking and model-registry documentation | ❌ Rejected for this report | It is suitable for product-behavior claims but does not provide a neutral platform/product ownership or build-versus-buy framework. It belongs in system-of-record research. |
| CNCF guest blogs and vendor-sponsored AI platform posts | ❌ Rejected | They are weaker than the CNCF working-group white paper for the claims in scope and can blend community education with vendor positioning. |
| Generic Linux Foundation platform-engineering articles | ❌ Rejected after comparison | No candidate found was more direct for the planned claims than the CNCF Platforms Working Group publication under the Linux Foundation umbrella. |
| Google-linked press article about production model failure | ❌ Rejected | The planned automation claims are supported by Google's own architecture documentation, so a non-primary press source is unnecessary. |

## Chapter 1 drafting guidance

Use these as synthesis inputs, not copy-ready claims without labels:

1. Open the ownership section with a failed handoff: a product team assumes the platform owns prediction quality while the platform team assumes it owns only endpoint health.
2. Define three layers in the responsibility diagram: product workload, platform experience and contracts, and internal or external capability providers.
3. Show that a golden path includes controls, evidence, telemetry, support, and rollback—not only templates.
4. Present automation maturity beside workload change rate and criticality so readers do not equate a numbered level with organizational status.
5. Make the build-versus-buy exercise compare four modes and require a full-lifecycle burden plus exit evidence.
6. State role scope through decision horizon, cross-team reach, and reversibility rather than unsupported scale.
7. Defer product-specific serving, registry, feature-store, and orchestration implementations to later chapters.

## Changelog

### 2026-08-23

- Added a qualified provider-contract boundary limited to duties directly established by actual service documentation and contract terms.
- Corrected Team Topologies metadata to publication on 2019-11-07 and modification on 2024-06-01 and narrowed the TVP finding to the page's stated guidance.
- Created the Chapter 1 platform-strategy research report from nine fully read official or authoritative pages.
- Added claim-level fact and synthesis labels, exact source URLs, dates, applicability limits, unresolved conflicts, and source-candidate decisions.
- Derived a bounded platform/product responsibility model, four-mode sourcing framework, and Senior/Staff/Principal decision-scope matrix without quantitative outcome claims.
- Split the AWS-supported design-principles list from the architectural inference that automation alone does not evidence governance or reliability controls, and documented that inference's assumption.
