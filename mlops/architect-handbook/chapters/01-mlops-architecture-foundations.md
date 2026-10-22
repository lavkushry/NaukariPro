# MLOps Architecture Foundations: From ML Lifecycle to Enterprise Platform Strategy

## Reader outcomes and prerequisites

**In this chapter:**

- [Reader outcomes and prerequisites](#reader-outcomes-and-prerequisites), [Why production ML is a systems problem](#why-production-ml-is-a-systems-problem), [ML lifecycle and operational feedback loops](#ml-lifecycle-and-operational-feedback-loops), [Architecture planes](#architecture-planes)
- [MLOps capability and maturity model](#mlops-capability-and-maturity-model), [System-of-record boundaries](#system-of-record-boundaries), [Platform and product-team responsibilities](#platform-and-product-team-responsibilities), [Build, buy, and managed-service decisions](#build-buy-and-managed-service-decisions)
- [Senior, Staff, and Principal decision scope](#senior-staff-and-principal-decision-scope), [Reference architecture and lifecycle flows](#reference-architecture-and-lifecycle-flows), [Production failure case study](#production-failure-case-study), [Architecture decision record exercise](#architecture-decision-record-exercise)
- [Interview questions and evaluation rubric](#interview-questions-and-evaluation-rubric), [Key takeaways](#key-takeaways), [Glossary additions and authoritative references](#glossary-additions-and-authoritative-references), [Changelog](#changelog)

**Handbook synthesis (bounded):** A production machine learning (ML) service is not a model wrapped in an endpoint. Its boundary is the chain of data contracts, code, configuration, training runs, evaluation evidence, artifacts, approvals, deployment state, runtime dependencies, user outcomes, and feedback. Machine learning operations (MLOps) names the operating discipline for that chain.

This boundary follows the production-system framing in the verified evidence set and is limited here to predictive ML; generative and agentic extensions are deferred. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

By the end of this chapter, a reader should be able to:

- draw an ML lifecycle as linked decision and feedback loops rather than a one-way pipeline;
- partition a platform into seven named architecture planes and state the authority, interface, and failure boundary of each;
- assess capability maturity without treating automation volume as organizational status;
- separate source, data, run, artifact, approval, deployment, risk, and incident records even when one product exposes several of them;
- assign platform, product, governance, security, and provider obligations at each lifecycle transition;
- compare build, buy, managed, and self-hosted modes using workload evidence, lifecycle burden, and exit constraints;
- distinguish Senior, Staff, and Principal scope by decision horizon and organizational reach; and
- reason from a failure trigger through propagation, detection, containment, recovery, and prevention.

The prerequisites are practical rather than product-specific. Readers should understand source control, data pipelines, model training and evaluation, deployment strategies, identity and access boundaries, distributed-system telemetry, and incident response. Familiarity with containers and Kubernetes helps with the control-plane analogy, but Kubernetes is not assumed to own ML lineage, model approval, or product risk. Kubernetes itself separates a control plane from worker nodes and assigns declared-state reconciliation to controllers. [`KUBERNETES-COMPONENTS-2026`](../sources/references.md#kubernetes-components-2026) [`KUBERNETES-CONTROLLERS-2024`](../sources/references.md#kubernetes-controllers-2024)

**Illustrative scenario:** A product team operates an online replenishment-ranking workload. It ingests product and inventory events, trains a candidate model, evaluates slices, promotes an approved artifact, serves rankings, and observes stock outcomes. This is a bounded teaching example, not production evidence. No stated behavior, scale, or result belongs to an actual organization.

**Assumptions:** The workload is predictive ML; product owners can define acceptance criteria; the organization has source control, identity management, an artifact store, and an incident process; and applicable law and sector obligations are assessed outside this chapter.

**Trade-off:** A single scenario keeps interfaces concrete but cannot represent every batch, streaming, generative, embedded, or safety-critical workload. Later chapters own product-specific training, serving, feature, observability, security, and generative-system designs.

## Why production ML is a systems problem

The replenishment model can pass an offline evaluation and still fail in production. An upstream producer can change the meaning of a numeric field without changing its type. Training and serving can compute a feature differently. A mutable model alias can move while a rollback procedure still points at the alias. The endpoint can meet its latency objective while ranking unsuitable products. These are boundary failures, not merely model failures.

Production ML inherits conventional software concerns and adds system-level risks because data influences behavior. Inputs can be entangled, so changing one input can alter the influence of others; data dependencies can be harder to discover than code dependencies; and external conditions can invalidate a tested system after release. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) Training can also be framed as compilation from code and training data, yet the resulting model still requires debugging, monitoring, rollback, and release controls. [`BRECK-MLTESTSCORE-2017`](../sources/references.md#breck-mltestscore-2017)

**Handbook synthesis (bounded):** Treat every dependency edge as an operational contract. For the edge from inventory events to feature computation, record the producer, consumer, semantic invariant, identity or time boundary, compatibility check, change-notification path, fallback, and evidence location. This contract model is an architectural judgment for predictive ML systems; it is not a schema prescribed by the cited papers.

The system boundary has at least five consequences:

1. **Quality is plural.** Offline model performance, service reliability, data fitness, security, policy compliance, and product outcome are separate signals. One green signal does not entail the others. The National Institute of Standards and Technology (NIST) Artificial Intelligence Risk Management Framework (AI RMF) treats validity and reliability, safety, security and resilience, accountability and transparency, explainability and interpretability, privacy, and fairness as interacting characteristics rather than substitutes. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)
2. **A release is a decision, not a file copy.** An artifact becomes eligible only after its identities, evaluations, risk decision, runtime compatibility, approver, and rollback target are linked.
3. **A dependency needs an owner.** Hidden consumers and unstable signals turn a producer's local change into a distributed incident. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015)
4. **Operations continue evaluation.** Unit and end-to-end tests do not establish continuing fitness when the external world changes; live monitoring is required to observe the deployed system. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015)
5. **Recovery evidence is part of readiness.** A candidate that cannot be traced, isolated, rolled back, bypassed, or retired safely is not operationally complete.

**Illustrative scenario:** The replenishment workload receives a valid-looking `inventory_age` field whose unit changes upstream. The model artifact is intact, the endpoint is available, and infrastructure tests pass. Rankings degrade because the semantic contract failed.

**Assumptions:** The field change is not malicious, schema validation checks type but not meaning, and outcome labels arrive after deployment.

**Trade-offs and failure modes:** Stronger semantic contracts, shadow comparisons, and versioned data references improve detection and diagnosis but add producer coordination, storage, and test maintenance. Copying unstable data improves replay but introduces staleness and retention cost. Blocking every ambiguous change reduces release risk but can delay urgent fixes.

**Security, governance, reliability, and cost:** **Handbook synthesis (bounded):** For this predictive workload and after contextual risk assessment, access enforcement plus trusted provenance and digest verification can provide evidence for detecting and rejecting unauthorized substitution when an admission policy consumes that evidence; neither proves data suitability. The control selection and effectiveness depend on implementation, threat model, and assessment. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026)

Governance identifies who may accept residual risk. Reliability defines user-facing service behavior. Cost includes evidence retention, validation compute, telemetry, and recovery drills, not only training and serving. The architecture planes and record classes below make these concerns assignable.

**Forward boundary:** Later chapters deepen data contracts, evaluation, and incident practice.

## ML lifecycle and operational feedback loops

Google's practitioner guidance defines an ML pipeline as infrastructure that gathers data, creates training data, trains models, and exports models to production. It treats deployment as iterative and recommends repeated launches, model-delta measurement, and training-serving skew monitoring. [`GOOGLE-RULESML-2025`](../sources/references.md#google-rulesml-2025) Google's predictive-ML architecture guidance adds data and schema validation, comparison against a baseline, segment evaluation, compatibility testing, pipeline metadata, and production monitoring. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

**Figure `fig-01-ml-lifecycle` — ML lifecycle and operational feedback loops:** [Diagram source](../diagrams/chapter-01/fig-01-ml-lifecycle.mmd) · [Text alternative](../diagrams/chapter-01/README.md#figure-fig-01-ml-lifecycle). The figure shows four kinds of movement that must not be collapsed:

- **data flow:** events and validated datasets move toward feature computation and training;
- **artifact flow:** code packages, evaluation bundles, and model artifacts move toward approval and serving;
- **control flow:** policies, triggers, approvals, desired deployment references, and rollback commands direct work;
- **telemetry and outcome flow:** service signals, data signals, model behavior, incidents, and product outcomes return to operators and future training.

The figure also separates accountability from mechanism. The product team owns workload intent, acceptance criteria, serving objectives, model behavior, and outcome review. A product review request passes through declared intent; it does not directly start training, select rollback, or create retirement state.

The named release and risk authority decides which action is permitted and authorizes a write to the passive desired deployment record. Approved and rollback identities, or retirement deactivation state, resolve into that record. The deployment controller watches desired state and is the only component that actuates the serving workload; controller status and workload telemetry return as observed deployment state.

**Handbook synthesis (bounded):** A useful lifecycle contract is:

`product event -> captured data -> validated data reference -> training run -> evaluated candidate -> approval decision -> immutable deployment reference -> serving workload -> prediction or action -> telemetry and outcome -> review, retraining, rollback, or retirement`

This sequence is a reasoning aid, not a required physical topology. Batch scoring can replace online serving; human review can sit before an action; an embedded model may have an intermittent telemetry path; and a low-change workload may retain manual transitions.

Feedback makes the loop architectural rather than decorative. Direct feedback occurs when model decisions affect which future data is selected for training. Hidden feedback occurs when separate systems influence each other indirectly through the world. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) In the replenishment scenario, ranked products receive more exposure and therefore produce more observed outcomes. The absence of an outcome for an unranked product is not neutral evidence.

NIST AI RMF 1.0 treats testing, evaluation, verification, and validation as continuing into operation through monitoring, incident tracking, updates, and recalibration. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Google's predictive-ML example separates training triggers and validation from reviewer approval and production promotion. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

**Handbook synthesis (bounded):** A continuous training (CT) trigger may create a candidate while production promotion remains a separate, policy-governed decision. This combined architecture rule is derived from the two cited boundaries; neither Google Cloud nor NIST individually prescribes the complete approval design. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

> **Decision:** The product risk owner and technical release owner define whether a trigger may train, evaluate, promote, roll back, or only request review.
>
> **Assumptions:** The trigger policy is workload-specific, resolves immutable identities, and records its decision evidence.
>
> **Trade-off:** More automation shortens repetitive handling and can make evidence collection consistent; it also increases the impact of a faulty policy or shared dependency.

**Failure modes:** The loop can retrain on model-influenced labels, accept stale outcomes, equate job success with model acceptance, or turn a noisy alert into repeated candidate creation. Delayed or missing ground truth can leave proxy signals green while product outcomes deteriorate.

**Security and governance:** Identity, intended-use boundaries, data rights, third-party controls, approval authority, and safe retirement remain in force throughout the loop. NIST calls for inventories, monitoring, incident practices, third-party risk policies, and safe decommissioning. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Reliability and cost:** Separate user-visible service health from pipeline freshness, data fitness, model behavior, and governance signals. Each family has different owners and actions. More frequent training can increase compute and review burden without improving a low-change workload. Google's guidance explicitly allows manual delivery where models change infrequently and advises gradual automation. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

**Forward boundary:** Later chapters specify trigger design, feature parity, evaluation, rollout, monitoring, and feedback-bias mitigation.

## Architecture planes

Planes are responsibility and authority boundaries, not mandatory clusters, networks, teams, or products. One service may implement several planes; one plane may span many services.

**Figure `fig-02-architecture-planes` — Seven architecture planes:** [Diagram source](../diagrams/chapter-01/fig-02-architecture-planes.mmd) · [Text alternative](../diagrams/chapter-01/README.md#figure-fig-02-architecture-planes). The figure keeps candidate bytes outside the control plane: training writes immutable artifact bytes to the artifact authority and store and sends only candidate identity and evaluation-evidence references to control. Serving resolves the approved immutable artifact from that authority after control records the release decision and approved immutable desired reference.

Kubernetes provides the sourced analogy, not the enterprise ML decomposition. In the reviewed Kubernetes v1.36 architecture, the application programming interface (API) server exposes the cluster API, etcd stores API data, and schedulers and controllers perform control-plane functions; worker-node components execute workloads. [`KUBERNETES-COMPONENTS-2026`](../sources/references.md#kubernetes-components-2026) Controllers observe state and move it toward declared intent, while higher-level workload resources maintain specified Pods. [`KUBERNETES-CONTROLLERS-2024`](../sources/references.md#kubernetes-controllers-2024) [`KUBERNETES-WORKLOADS-2026`](../sources/references.md#kubernetes-workloads-2026)

### Control plane

**Handbook synthesis (bounded):** The ML control plane accepts declared intent, writes authoritative desired state, invokes policy, schedules reconciliation, records observed status, and issues corrective action. It can coordinate training requests, promotion decisions, deployment references, rollback, and retirement. The transferable pattern is `declared intent -> authoritative state -> reconciliation -> observed status -> corrective action`; Kubernetes supports the analogy but does not define a complete enterprise ML control plane. [`KUBERNETES-CONTROLLERS-2024`](../sources/references.md#kubernetes-controllers-2024)

In the replenishment workload, the control plane receives a promotion request for a candidate digest, verifies required evidence, records approval, and declares the serving revision. Its primary failure mode is authority confusion: two systems can both appear able to promote. Centralizing authority simplifies audit and reconciliation but can create a high-impact dependency.

**Handbook synthesis (bounded):** Assuming organization-controlled identities and a tailored risk assessment, this control plane should select identification and authentication, scoped access enforcement, protected decision logging, and separately governed emergency access with named owners and reviewable evidence. NIST SP 800-53 Rev. 5 supplies tailorable control families for those concerns; it does not make this list a universal baseline or establish effectiveness for this workload. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025)

Cost concentrates in control-plane reliability, integration, and policy maintenance.

### Data plane

**Handbook synthesis (bounded):** The data plane carries workload data under declared policy: raw events, validated datasets, online features, batch features, predictions, and outcome observations. It owns movement and enforcement at the data path, not the truth of product semantics by itself.

The replenishment data plane moves inventory events into validated storage and feature views. A useful contract includes schema, semantic invariants, event-time behavior, identity, classification, retention, deletion, and consumer notification. Shared paths improve reuse; workload-specific paths preserve local semantics. Failure modes include silent unit changes, skew, late data, unauthorized access, and feedback contamination.

**Handbook synthesis (bounded):** After data classification and threat assessment, candidate controls include cryptographic protection for applicable transmission and storage paths, identity-based access enforcement, and protected event logging. These controls produce evidence but do not by themselves establish suitability, lawful use, or effective protection. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025)

Minimization remains a workload and governance decision. Storage, transfer, validation, and replay dominate cost.

### Training plane

**Handbook synthesis (bounded):** The training plane transforms versioned code, configuration, and data references into candidate artifacts plus run and evaluation evidence. A successful training job creates a candidate, not an approval.

In the scenario, a training request resolves code, environment, feature definitions, data window, and prior-model pointer. It emits a model digest, metrics, slice results, logs, and lineage references. Reproducibility competes with execution flexibility and cost; where exact identity is infeasible, the required tolerance should be explicit. Failure modes include unpinned dependencies, non-replayable data, leakage, resource exhaustion, and evidence published after a partial failure.

**Handbook synthesis (bounded):** Under the same risk-assessment assumption, process isolation and scoped secret access are candidate exposure controls. Dependency integrity plus artifact signing must be paired with trusted provenance-envelope and subject-digest verification and a policy admission step before they can support detection and rejection of an unauthorized packaged artifact. Signing alone does not reduce attack paths or establish model validity. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026) [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026)

Compute efficiency must be measured against diagnosis and recovery needs.

### Serving plane

**Handbook synthesis (bounded):** The serving plane resolves an approved immutable model identity and returns batch, streaming, or online outputs with runtime telemetry. It enforces the deployment contract but does not decide whether the model's product behavior remains acceptable.

The replenishment service loads the approved digest and records its runtime revision. A mutable convenience alias may select a version, but rollback evidence should preserve the resolved version. In MLflow 3.15.1, aliases are mutable named references and fixed stages have been deprecated since version 2.9.0. [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026)

Serving trades latency against batching, utilization against isolation, and progressive exposure against operational complexity. Failure modes include incompatible runtime dependencies, alias races, stale caches, partial rollout, and silent fallback.

**Handbook synthesis (bounded):** For this online path and after threat assessment, candidate controls include verified artifact admission, least-privilege runtime and deploy identities, network-boundary enforcement, and workload-specific abuse controls; their implementation and assessment are deferred. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026)

### Observability plane

**Handbook synthesis (bounded):** The observability plane preserves separate views of service health, pipeline and data health, model behavior, and governance or product impact. It links signals to the exact data, artifact, deployment, and decision identities active at observation time.

For the replenishment workload, endpoint availability cannot substitute for feature freshness or ranking acceptance. Google defines a service-level indicator (SLI) as a measurement of service delivered to users and a service-level objective (SLO) as a target reliability level. Candidate SLI types include availability, latency, quality, pipeline freshness, pipeline correctness, pipeline coverage, and storage durability. [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018)

More signal coverage raises telemetry cost, alert noise, and sensitive-data exposure. Failure modes include aggregate dashboards hiding affected slices, missing deployment labels, alert loops without an owner, and delayed ground truth.

### Security and governance plane

**Handbook synthesis (bounded):** The security and governance plane expresses intended use, control tier, identity policy, evidence requirements, approval authority, third-party controls, residual risk, incident decisions, and retirement. It supplies policy decisions to other planes and receives evidence back; it is not a document portal detached from execution.

NIST AI RMF 1.0 is voluntary, rights-preserving, non-sector-specific, and use-case agnostic. It organizes outcomes into Govern, Map, Measure, and Manage, with Govern cross-cutting, and states that these functions are not a checklist or required sequence. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) The NIST Playbook suggests risk scales, oversight tiers, and approval, conditional-approval, or disapproval paths as optional actions rather than mandates. [`NIST-AIRMFPLAYBOOK-2023`](../sources/references.md#nist-airmfplaybook-2023)

In the scenario, this plane records intended use, approvers, evaluation expectations, permitted data, deployment constraints, and stop conditions. Failure modes include policy that cannot be enforced, an exception without expiry, missing third-party contingency, and no decommissioning owner. Strong control depth improves accountability but adds review and evidence cost. Applicable legal duties remain a separate, jurisdiction-specific analysis.

### Platform experience plane

**Handbook synthesis (bounded):** The platform experience plane turns reusable capabilities into supported journeys through APIs, command-line interfaces, templates, documentation, policy feedback, service expectations, and escalation paths. It owns the contract and user experience even when another internal team or external provider implements a capability.

The Cloud Native Computing Foundation (CNCF) defines a cloud-native platform as an integrated collection of capabilities presented around user needs. It assigns platform teams user research, roadmap planning, and interfaces, while capability implementation may sit elsewhere. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

In the scenario, the experience plane offers a supported route from training request to evidence-backed promotion. Standardization competes with specialized needs. Failure modes include a portal that hides unsupported provider behavior, a golden path with no recovery contract, and abstractions that prevent diagnosis.

**Handbook synthesis (bounded):** Under the tailored-control assumption above, the platform contract should expose selected guardrails, rejection reasons, evidence, and escalation rather than hide them behind a portal. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) Cost includes product discovery, support, adoption, deprecation, and migration.

The seven-plane split prevents a familiar ownership error: declaring that a registry, pipeline, cluster, or dashboard is the MLOps platform. Each is a capability inside a larger decision system.

**Forward boundary:** Later chapters specify concrete controllers, policy engines, data and feature paths, training systems, inference patterns, telemetry and SLO implementation, security and governance controls, and platform-product journeys. This chapter keeps only the authority, evidence, failure, cost, and operating contracts needed to compare those designs.

## MLOps capability and maturity model

The model below is **Handbook synthesis (bounded)**. It combines automation capability, balanced production-readiness evidence, governance, reliability, and platform operating practice. It is not a standard, compliance score, or fixed sequence. A low-change workload can remain deliberately manual if its controls, evidence, and recovery posture fit its risk. Google's predictive-ML guidance separates manual delivery, automated ML pipelines, and automated continuous integration and continuous delivery (CI/CD) for pipeline changes, and allows manual delivery when change is infrequent. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

The ML Test Score contributes a useful coverage warning. It defines 28 checks across features and data, model development, ML infrastructure, and monitoring. It gives partial credit for documented manual execution, full credit for repeated automation, and uses the minimum of the four area totals so strength in one area cannot hide weakness in another. [`BRECK-MLTESTSCORE-2017`](../sources/references.md#breck-mltestscore-2017)

Its dominant context was supervised learning with repeated training and low-latency serving, and its study applied the rubric through structured interviews with 36 Google teams. Use it as a diagnostic taxonomy within that boundary, not as a universal maturity standard. [`BRECK-MLTESTSCORE-2017`](../sources/references.md#breck-mltestscore-2017)

### Stage 0: Explicit manual control

The workload has named owners, version identities, a documented release checklist, approval evidence, rollback or bypass instructions, and an inventory entry. Execution may be manual. The maturity test is whether a second operator can identify what changed, who approved it, what is running, and how to recover.

**Illustrative scenario:** The replenishment team trains infrequently and promotes through a reviewed runbook. This is bounded to the teaching workload. Operator effort and slower repetition trade against lower automation investment. Failure modes are skipped steps, stale evidence, and person-dependent recovery.

**Handbook synthesis (bounded):** This example assumes ordinary and emergency access paths are separately authorized and logged under locally selected controls; that is a scenario condition rather than a universal security baseline. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025)

Cost includes review time and rehearsal. The next investment should target the manual transition with the largest release or recovery risk, not automate every step.

### Stage 1: Repeatable evidence

Source, data, run, artifact, evaluation, approval, deployment, and rollback identities are captured consistently. Tests are repeatable; manual execution is documented; telemetry names the active deployment. The operational question moves from "what happened?" to "did the recorded evidence satisfy the declared policy?"

The trade-off is metadata and retention overhead. Failure modes include collecting records without linking them, making dashboards canonical, and retaining sensitive evidence beyond its purpose. Governance defines retention and reviewer independence; operations test record restoration.

### Stage 2: Automated candidate pipeline

Data and schema validation, training, evaluation, compatibility checks, metadata capture, and candidate registration run as a pipeline. Google's predictive-ML pattern includes these capabilities and separates them from promotion. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

Faster and more consistent candidate creation enlarges the shared failure radius. A faulty common component can produce many invalid candidates.

**Handbook synthesis (bounded):** This stage assumes locally selected execution-isolation controls and verified dependency or provenance evidence appropriate to the packaged artifacts; implementation and effectiveness require workload assessment. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026)

Cost control needs workload-aware scheduling and evidence-retention policy. Recovery cancels or quarantines candidates without changing production.

### Stage 3: Governed continuous delivery

Three independently gated subjects operate at this stage. Continuous integration and continuous delivery (CI/CD) builds, tests, and deploys pipeline code, serving code, and their configuration. CT creates and evaluates a candidate model but does not authorize production.

The model-release function splits into two logical authorities. An authorized release workflow consumes the approved immutable model and runtime bundle and writes the passive desired deployment reference. A deployment controller watches that reference, alone actuates runtime through the serving mechanism, and records reconciliation status.

If one product implements both roles, separately gated identities and permissions preserve the writer and actuator authorities. Approval may be a named human decision or an automated workload-specific policy decision, but a successful CT run or software build does not grant production authority by itself.

**Handbook synthesis (bounded):** This separation combines Google's pipeline-change and candidate-creation boundaries with a workload-specific promotion decision; neither cited source individually prescribes the complete model-release controller. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

Release speed competes with policy and controller complexity. Failure modes include a policy bug that authorizes broad rollout, a shared control-plane outage, or rollback that restores service but not data compatibility. NIST calls for pre-deployment and in-operation testing, production monitoring, and documented response and recovery. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Cost includes resilient control-plane operation, canary capacity, and on-call readiness.

### Stage 4: Portfolio platform

Reusable journeys serve multiple workloads through explicit contracts, optional capabilities, exception and deprecation paths, provider abstraction where justified, shared evidence interfaces, and portfolio-level risk and cost review. CNCF recommends platform-as-product, self-service, optional composition, and a thin integration layer for cloud-native delivery. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

Organizational leverage competes with abstraction, migration, and support burden. Failure modes include standardizing a local preference, hiding provider limits, funding build work without operations, and accumulating permanent exceptions. Within this bounded maturity model, security and governance owners select shared guardrails while product teams retain workload accountability; control implementation remains workload-specific. Portfolio cost includes platform product work, provider concentration, adoption support, and retirement.

NIST AI RMF's Govern, Map, Measure, and Manage functions can be used to test every stage, but the framework explicitly does not define a checklist or execution order. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Amazon Web Services (AWS) guidance also joins ownership and automation with protection, resiliency, reusability, reproducibility, resource trade-offs, cost awareness, and continuous improvement; that is AWS practitioner guidance, not a cross-vendor standard. [`AWS-MLDESIGN-2025`](../sources/references.md#aws-mldesign-2025)

**Forward boundary:** Later chapters define lineage schemas, evidence stores, pipeline orchestration, test design, deployment controllers, release strategies, multi-tenancy, capacity, financial operations (FinOps), and platform evolution. The five stages remain a diagnostic of evidence, recovery, governance, security, cost, and operating readiness rather than a mandate to maximize automation.

## System-of-record boundaries

During an incident, "the registry says champion" is not enough. An operator needs the exact artifact digest, source run, data reference, evaluation bundle, approval decision, deployment revision, runtime configuration, observed signals, and rollback target that applied at the relevant time.

**Figure `fig-03-systems-of-record` — Linked systems of record:** [Diagram source](../diagrams/chapter-01/fig-03-systems-of-record.mmd) · [Text alternative](../diagrams/chapter-01/README.md#figure-fig-03-systems-of-record). The figure distinguishes authoritative record classes from catalogs and dashboards. The dataset and workload-data store receives producer bytes; the data and feature record receives immutable or versioned identity, event boundary, and contract metadata rather than becoming the workload-data sink.

The canonical deployment record is passive. An authorized workflow writes its desired immutable reference; the deployment controller watches that desired state and actuates the runtime workload. Controller reconciliation status plus workload telemetry update observed state. Records supply evidence and desired facts; they do not issue runtime control.

The classification below is **Handbook synthesis (bounded)**: each fact class should have a canonical record joined through immutable or versioned identities, while search, catalog, and dashboard views remain derived. NIST and Google Cloud support traceability outcomes but do not prescribe this schema. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

Google Cloud's predictive-ML metadata example records pipeline and component versions, execution context, parameters, produced artifacts, prior-model pointers, and evaluation metrics. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) The example supports linked lineage evidence within that documented pattern; it does not establish one enterprise record schema.

### Source and configuration records

These records identify code revisions, pipeline definitions, dependency locks, environment descriptions, policy versions, infrastructure configuration, and feature logic. The authority is usually source control plus approved configuration state, not a copied value in a run dashboard.

The replenishment workload links its training and serving revisions to source and configuration identities. Strict immutability competes with emergency change speed. Failure modes include uncommitted runtime edits and secret values copied into evidence.

**Handbook synthesis (bounded):** For this record boundary, locally selected access and audit controls should protect approved change paths and evidence should store references to secrets rather than secret contents; the applicable mechanism depends on the organization's threat model. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) Cost arises from retention, review, and configuration reconciliation.

### Data and feature records

These records identify source datasets or event boundaries, schema and semantic contracts, feature definitions, time windows, classifications, access decisions, retention, and deletion state. They distinguish a data pointer from a stored copy and state the reproducibility tolerance.

The scenario records the exact inventory-event boundary and feature definition used for training. Replayability competes with storage, privacy, and staleness. Failure modes include an immutable identifier pointing to mutable content, late-arriving data changing a window, and deletion obligations not propagating. Security and governance decide access and retention.

### Run and artifact records

In MLflow 3.15.1, a run records parameters, metrics, timing, and output artifacts; its backend store persists run metadata while an artifact store holds large outputs such as model weights and data files. [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026) **Handbook synthesis (bounded):** Tracking metadata, artifact storage, model registration, and deployment state are separate record classes even when one product presents several together. The MLflow sources describe product behavior but do not prescribe this enterprise authority boundary. [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026) [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026)

The replenishment run record links inputs, execution context, outputs, logs, and evaluation evidence. The artifact record identifies model and package bytes by immutable digest. Rich evidence increases storage cost and sensitive-data exposure. Failure modes include successful metadata publication with missing artifacts, artifacts overwritten at a stable path, and retention mismatch.

**Handbook synthesis (bounded):** Assuming these records are needed for release and recovery, the organization should select access enforcement, integrity verification, backup, and recovery-test evidence appropriate to their classification and recovery objectives. NIST supplies tailorable controls for these concerns but does not establish one universal implementation or outcome. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025)

### Model and approval records

In MLflow 3.15.1, the registry workflow supports registered models, versions, aliases, tags, descriptions, source-run information, and creation timestamps. [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026) **Handbook synthesis (bounded):** Those capabilities do not make a registry the full governance system of record; that authority boundary remains workload- and organization-specific. [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026) [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026)

The model record describes candidate and version identity; the approval record names the decision, policy version, evidence set, approver, conditions, expiry or review trigger, and residual risk. A mutable alias is useful for discovery or routing, but an audit record resolves it to the immutable version observed at decision time. Convenience competes with historical certainty. Failure modes include alias reassignment racing deployment and approval represented only by a tag.

### Deployment and runtime records

These records identify desired deployment state, resolved artifact, environment, runtime and configuration versions, rollout state, active endpoints or jobs, traffic allocation, observed status, and rollback target. They answer "what was intended?" and "what was actually active?"

The scenario ties each prediction log to a deployment identity. Telemetry cardinality and storage compete with diagnosis. Failure modes include partial rollout, configuration drift, stale routing, and rollback to an artifact incompatible with present data.

**Handbook synthesis (bounded):** For qualifying packaged artifacts, signing should be paired with provenance and digest verification plus policy admission; deploy and emergency identities should be scoped and their actions logged under locally selected controls. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025) [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026) Reliability requires reconciliation and tested recovery.

### Risk, incident, and retirement records

NIST AI RMF 1.0 calls for an AI-system inventory, periodic review, third-party risk policy, incident practices, and safe decommissioning. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) These records capture intended and prohibited use, affected context, control tier, third-party components, risk decisions, exceptions, incidents, recovery actions, dependents, retention duties, and deactivation.

The scenario links an incident to the affected deployment, data contract, decisions, and recovery evidence. Audit depth competes with sensitive context and operational burden. Failure modes include an inventory that is not connected to runtime, an exception without review, and retirement that leaves scheduled training active.

Supply-chain Levels for Software Artifacts (SLSA) v1.2 Build provenance binds an output package digest to how it was produced. Higher Build levels add authenticity, control-plane-generated provenance, hosted builds, and isolation requirements. Its Build track is scoped to software package production and can omit some resolved dependencies. [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026)

**Handbook synthesis (bounded):** SLSA Build provenance is one artifact-integrity record. It does not establish dataset fitness, model validity, approval legitimacy, or complete ML lineage. This combined boundary joins SLSA's artifact scope to NIST's separate AI-risk evidence and decision semantics; neither source prescribes a complete ML lineage authority. [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Forward boundary:** Later chapters define source and infrastructure controls, dataset versioning, feature stores, experiment tracking, artifact storage, registry and approval workflows, deployment state, governance operations, and decommissioning. The durable foundation here is the separation of canonical facts, immutable or versioned identity links, access and retention decisions, failure recovery, and non-authoritative views.

## Platform and product-team responsibilities

A failed handoff often starts with two plausible statements: "the platform owns production" and "the product team owns the model." Neither identifies who decides whether an evaluation is sufficient, who owns endpoint restoration, who accepts product risk, who communicates a provider incident, or who retires dependent pipelines.

CNCF's cloud-native platform guidance frames a platform as capabilities presented around user needs and assigns the platform team user research, roadmap planning, and interfaces, while implementation may reside with another internal team or managed provider. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) Microsoft frames a workload as application resources, custom code, AI models, data, and supporting infrastructure that achieve a business outcome; workload teams focus on that outcome while centralized teams provide shared services, guidance, and guardrails. [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

The following model is **Handbook synthesis (bounded)**. It is a starting responsibility contract, not a universal organization chart. Each boundary is linearized as platform, product, independent authority, and contracted-provider obligations.

- **Supported journey**
  - **Platform:** Own the interface, documentation, onboarding, support, deprecation, and platform service expectations.
  - **Product or workload:** Select a supported path or justify an exception.
  - **Shared or independent authority:** Agree adoption criteria, exception expiry, and migration.
  - **Capability provider when contracted:** Operate the service within documented limits and support interfaces.
- **Data and model logic**
  - **Platform:** Provide hooks, identity, storage interfaces, and baseline controls.
  - **Product or workload:** Own feature logic, training intent, acceptance criteria, and product behavior.
  - **Shared or independent authority:** Governance or independent reviewers may approve defined risk evidence.
  - **Capability provider when contracted:** Honor contracted data-location, retention, deletion, access, and processing boundaries.
- **Delivery**
  - **Platform:** Operate reusable orchestration, policy enforcement points, artifact interfaces, and deployment mechanisms.
  - **Product or workload:** Supply workload configuration, evidence, release intent, and rollback conditions.
  - **Shared or independent authority:** The release authority resolves conflicts and records the decision.
  - **Capability provider when contracted:** Give contracted change and deprecation notice; document compatibility and service-limit changes.
- **Reliability**
  - **Platform:** Own platform dependency objectives, telemetry, runbooks, breaking-change notice, and restoration.
  - **Product or workload:** Own end-to-end workload objectives, application telemetry, user-impact response, and workload runbooks.
  - **Shared or independent authority:** Name incident command and escalation before release.
  - **Capability provider when contracted:** Provide contracted telemetry, incident escalation, service recovery support, and status communication.
- **Security and governance**
  - **Platform:** Provide organization guardrails, identity integration, audit export, and an approved capability catalog.
  - **Product or workload:** Classify data, assess workload and dependency risk, and operate within approved use.
  - **Shared or independent authority:** Security, legal, governance, or risk owners retain their decision authority.
  - **Capability provider when contracted:** Execute contracted security and vulnerability response and expose agreed audit evidence or export.
- **Provider dependency**
  - **Platform:** Operate provider integration and service escalation.
  - **Product or workload:** Own workload fallback behavior and product-communication inputs.
  - **Shared or independent authority:** Contract owner, platform, and product coordinate contingency and exit.
  - **Capability provider when contracted:** Support contracted portability, evidence export, transition, and termination obligations.
- **Product outcome**
  - **Platform:** Measure platform adoption and capability health.
  - **Product or workload:** Own the business outcome, user experience, model behavior, and outcome measurement.
  - **Shared or independent authority:** A platform limitation can block release but does not absorb product accountability.
  - **Capability provider when contracted:** Meet the contracted capability boundary; do not own internal workload acceptance or product outcomes unless explicitly contracted.

NIST calls for documented roles and communication lines plus executive responsibility for development and deployment risk decisions. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Google's SLO approach calls for stakeholder-approved objectives, an empowered owner, a written error-budget policy, and refinement. [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018) Microsoft also advises making compliance, observability, performance, support, budget, and change-control expectations explicit in shared-responsibility discussions. [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

**Handbook synthesis (bounded):** For a managed capability, the operating contract should explicitly allocate provider obligations for service operation and documented limits; security and vulnerability response; change and deprecation notice; data location, retention, and deletion; telemetry and audit export; incident escalation and recovery support; and portability and termination.

This recommendation applies only where the actual service documentation and contract directly establish each obligation. It does not assert that every provider offers these capabilities or transfer platform-integration, workload-acceptance, product-outcome, or internal incident-command accountability. [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025) [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025) [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

**Illustrative scenario:** The replenishment endpoint meets the platform availability objective, but a product acceptance signal breaches its bound. The product owner decides whether workload behavior remains acceptable. The platform keeps deployment and rollback mechanisms available; the risk authority decides whether operating conditions remain permitted. If the shared deployment API breaks its published contract, the platform owns capability restoration.

If a managed provider causes the failure, the provider supplies the contracted incident notice, telemetry or audit export, escalation path, and recovery support. Internal owners still coordinate containment, workload fallback, risk acceptance, recovery verification, and product communication.

**Assumptions:** Each decision has one accountable owner even when several teams execute work. Small organizations may assign several decisions to one person without merging the records.

**Trade-offs and failure modes:** Centralization can make controls consistent but can separate decisions from workload context. Decentralization can improve context but duplicate controls and create uneven evidence. A golden path can reduce cognitive load yet become a bottleneck if exceptions lack an owner. Within this bounded responsibility model, applicable security and governance decisions retain their named authority; product teams do not transfer user-impact accountability to a platform abstraction. Cost allocation must include platform support and workload-specific operations.

Team Topologies advises a thinnest viable platform no thicker than needed and notes that it can be a page naming approved cloud services plus usage guidance. [`TEAMTOPOLOGIES-TVP-2019`](../sources/references.md#teamtopologies-tvp-2019) Start with the smallest contract that closes an observed responsibility or delivery gap.

**Forward boundary:** Later chapters define detailed team topology, service ownership, and operating models. This chapter keeps the accountable platform, workload, independent-authority, and provider handshakes visible across security, cost, reliability, incident response, and exit.

## Build, buy, and managed-service decisions

"Build versus buy" hides at least four modes: external software as a service (SaaS) or model API, managed cloud capability, self-hosted third-party software, and custom implementation. A platform can compose all four. Evaluate each capability separately rather than choosing one mode for the whole platform.

Microsoft frames SaaS, platform as a service (PaaS), and custom AI choices through data control, customization, upkeep, performance, expertise, security, and compliance. [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026) AWS recommends comparing custom and pre-trained models using data, task specificity, performance, expertise, development time, infrastructure, security, and long-term maintenance. [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025) These are vendor comparison factors, not universal selection outcomes.

### Decision dimension: workload and differentiation

State the product outcome, acceptance envelope, change rate, data sensitivity, latency or freshness profile, availability and recovery objectives, integration surfaces, and evidence required for release. Then classify whether the capability differentiates the product or supplies common infrastructure.

In the scenario, ranking policy is workload-specific while artifact storage is a common capability. Building both would absorb different long-term obligations. The failure mode is declaring a capability differentiating because the team has already customized it. Revisit the decision when requirements or provider capabilities change.

### Decision dimension: control, security, and governance

Compare data location, identity, network boundaries, customization, auditability, supply-chain evidence, third-party controls, support terms, and applicable compliance constraints. NIST calls for policies, monitoring, controls, and contingency processes for third-party data, software, AI systems, and pretrained models. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

Managed service does not mean managed workload risk; custom implementation does not imply compliance. The failure mode is treating an implementation label as control evidence.

**Handbook synthesis (bounded):** Under local review policy, security and governance reviewers should examine actual data paths, permissions, artifacts, contracts, and incident processes rather than infer controls from the sourcing label. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

### Decision dimension: lifecycle economics and operations

Model acquisition, integration, identity and network work, data movement, migration, upgrades, patches, capacity, observability, on-call, support, incident coordination, training, evidence retention, and retirement. AWS identifies infrastructure, personnel, maintenance, scaling, upgrades, utilization, and pricing model as managed-service cost inputs but does not establish a workload-neutral cost result. [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025)

The failure mode is comparing license or compute price while excluding operations and exit. A managed service can remove some toil and add provider dependency; self-hosting can increase control and add staffing and recovery burden. Sensitivity analysis should expose which assumptions reverse the decision.

### Decision dimension: portability and exit

Require exportable artifacts, metadata, logs, and decision evidence; stable interfaces; a dependency inventory; tested restore or redeploy; contractual termination; and a replacement path. CNCF recommends a thin platform layer over capability providers with optional and composable offerings in its cloud-native delivery scope. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

Abstraction has a cost. A thin interface can preserve options, but a lowest-common-denominator layer can hide valuable provider behavior and obstruct diagnosis. The failure mode is an exit plan that exports bytes without semantics, history, or replay capability.

### Decision dimension: evidence and review triggers

Prototype the assumption with the highest decision risk using representative workload conditions. Record the owner, source evidence, accepted trade-offs, rejected modes, exception, review trigger, and retirement condition in an architecture decision record (ADR).

The mode comparison is **Handbook synthesis (bounded)**. It compares workload requirements, lifecycle burden, operating ownership, and exit evidence; none of the cited vendor or platform sources prescribes the combined decision rule. [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025) [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025) [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026) [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

Read each sourcing mode through the same three keys: selection evidence, exposed burden, and exit proof.

- **External SaaS or model API**
  - **Select when:** Behavior and contractual controls fit a non-differentiating need.
  - **Burden to expose:** Provider concentration, opaque change, data handling, unit economics, quotas, and regions.
  - **Exit evidence:** Exportable data and logs, a substitutable interface, fallback, and a termination plan.
- **Managed cloud capability**
  - **Select when:** Removed operations justify service coupling and constraints.
  - **Burden to expose:** Shared-responsibility gaps, service limits, pricing, regions, and constrained customization.
  - **Exit evidence:** Artifact and metadata export, a dependency inventory, and tested redeployment.
- **Self-hosted third-party software**
  - **Select when:** Control, portability, extension, or deployment constraints justify internal operation.
  - **Burden to expose:** Upgrades, patches, security response, specialized staffing, scaling, and on-call.
  - **Exit evidence:** Reproducible deployment, backups, versioned configuration, an upgrade path, and a support contingency.
- **Custom implementation**
  - **Select when:** A material differentiator or hard requirement is unmet elsewhere.
  - **Burden to expose:** Product roadmap, reliability, security, adoption, opportunity cost, and succession.
  - **Exit evidence:** Stable interfaces, maintained documentation, transition state, and a retirement plan.

> **Decision:** Select the thinnest composition that satisfies measured workload requirements and preserves accountable ownership.
>
> **Assumptions:** Requirements, owners, provider obligations, lifecycle burdens, and exit evidence are explicit.
>
> **Trade-off:** Thinner managed composition can reduce internal operation and increase provider dependency; thicker self-hosted or custom composition can increase control and transfer more lifecycle obligations inward.

**Forward boundary:** Later chapters supply workload-requirement methods, control assessment, cost and capacity models, migration, and portability patterns. The decision here remains reviewable only when its assumptions, operating ownership, security and governance boundary, failure response, lifecycle cost, and reversal conditions are recorded.

## Senior, Staff, and Principal decision scope

The role model below is **Handbook synthesis (bounded)**. Titles vary across employers. The distinction here is decision horizon, cross-team reach, organizational constraints, reversibility, and platform evolution, not unsupported team size, request volume, budget, or title prestige. It builds on platform-as-product and shared-workload guidance without claiming that either source defines career levels. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

### Senior scope

A Senior architect or engineer owns a consequential workload or platform capability end to end. The decision horizon covers implementation, release, operation, and the next material change. Expected artifacts include an interface contract, dependency map, evaluation and release gates, service objectives, telemetry, security review inputs, cost assumptions, runbook, rollback proof, and ADR.

**Illustrative scenario:** A Senior engineer designs the replenishment workload's promotion gate. They ensure that data, model, compatibility, and policy evidence resolve to immutable identities; define alert and rollback behavior; and test the operator path. This is a bounded role example, not a staffing prescription.

The trade-off is local delivery speed against reusable design. The failure mode is a component that functions in isolation but has no support boundary, production evidence, or recovery path. Within this bounded role model, the Senior decision records the applicable security and governance review interface rather than representing it as a checkbox. Cost analysis covers the capability's build and operational burden. A Senior decision should name which cross-team issue requires Staff escalation.

### Staff scope

A Staff architect owns a cross-team journey or capability portfolio. The horizon includes adoption, common contracts, exception policy, provider selection, migrations, deprecation, shared operations, and the effect of a local choice on several workloads. Evidence includes representative requirements from consuming teams, a responsibility map, reliability and cost boundaries, provider exit analysis, adoption and support signals, and transition states.

**Illustrative scenario:** A Staff architect turns several workload-specific promotion scripts into a supported evidence contract while preserving workload-specific acceptance policies. The platform standardizes identity, policy hooks, deployment records, and rollback evidence; product teams keep product thresholds and risk context.

The trade-off is consistency against specialized needs. Failure modes include standardizing the first team's preference, moving cognitive load into hidden exceptions, or promising a platform contract that capability providers do not meet. Within this bounded role model, the Staff decision names the selected common enforcement boundary and exception authority; neither is a universal control prescription. Cost analysis includes migration, support, and deprecation rather than only implementation. A Staff decision should identify enterprise constraints that require Principal resolution.

### Principal scope

A Principal architect owns enterprise boundaries and multi-year evolution. The horizon includes investment allocation, operating model, systemic and correlated risk, vendor concentration, governance interfaces, capability succession, portfolio migration, and retirement. Evidence includes strategic constraints, scenario analysis, portfolio dependencies, funding and capability models, transition architecture, and a review cadence.

**Illustrative scenario:** A Principal architect decides whether model promotion authority remains distributed across business units or converges on a federated control contract. The decision accounts for jurisdiction, product criticality, provider concentration, organizational autonomy, incident command, and migration sequencing without forcing one implementation everywhere.

The trade-off is enterprise coherence against local autonomy and transition cost. Failure modes include optimizing one layer while creating lock-in, fragmented accountability, or an unfunded operating obligation. Within this bounded role model, the Principal decision records which security and governance authorities and escalation paths remain independent. Cost analysis includes stranded capability, parallel operation during migration, and long-term exit. A Principal decision should define what remains locally reversible and which boundary is enterprise-wide.

**Handbook synthesis (bounded):** Across all levels, evidence quality matters more than document volume. Senior scope tests whether a workload decision can operate; Staff scope tests whether a contract works across contexts; Principal scope tests whether enterprise boundaries can evolve without losing accountability or recovery. This model does not define cross-employer career levels. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

**Forward boundary:** Later chapters own detailed organizational topology, career calibration, operating-model implementation, platform portfolio governance, and multi-year platform-evolution methods.

## Reference architecture and lifecycle flows

The reference architecture starts with a decision record, not a vendor box. An intake record identifies intended use, product owner, technical owner, affected context, data boundaries, risk owner, and required service and model evidence. From there, control, data, artifact, and telemetry flows cross the seven planes.

The following flow is **Handbook synthesis (bounded)** for a predictive ML workload:

1. **Intake and intent.** The product team records the business outcome, intended and prohibited use, acceptance criteria, data classification, reliability objective, and fallback. Governance assigns a control tier and decision owners.
2. **Data admission.** Data and feature contracts resolve producers, semantics, identities, time boundaries, access, retention, and deletion. Validation produces evidence, not merely a pass flag.
3. **Candidate construction.** The control plane creates a training request. The training plane resolves source, configuration, environment, and data references, then emits a candidate artifact and run evidence.
4. **Candidate evaluation.** Data, model, slice, compatibility, security, and operational tests produce an evidence bundle. Google's predictive-ML pattern includes data and schema validation, model-versus-baseline and segment evaluation, compatibility testing, pipeline metadata, and production monitoring. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)
5. **Approval.** Policy checks the evidence and routes an approval, conditional approval, or rejection to the named authority. **Handbook synthesis (bounded):** Training success and registry publication do not imply production approval; the approval policy and authority remain workload-specific, and neither cited source alone defines the combined architecture. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)
6. **Promotion and reconciliation.** An approved immutable artifact and configuration become the immutable desired deployment reference. A deployment controller watches that passive record, actuates the serving workload, records reconciliation status, and combines it with workload telemetry to establish observed state.
7. **Operation.** User requests or batch inputs traverse the data and serving planes. Telemetry links service, pipeline, data, model, product, and governance signals to the active deployment.
8. **Review and response.** Owners continue, constrain, investigate, retrain, roll back, bypass, or stop according to written policy. NIST states that systems with unacceptable risk should cease development or deployment safely until risk can be managed. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)
9. **Retirement.** The system identifies dependents, preserves required evidence, deactivates endpoint and scheduled work, removes access, communicates replacement, and records residual obligations. NIST includes safe decommissioning and procedures to supersede, disengage, or deactivate systems that violate intended use. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

Reliability and AI-risk controls meet at decisions but retain separate semantics. Google's site reliability engineering (SRE) guidance defines SLIs and SLOs around service delivered to users and calls for an owner, stakeholder agreement, and written error-budget policy. [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018) NIST AI RMF governs intended use, trustworthiness evidence, residual risk, monitoring, response, and retirement. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Handbook synthesis (bounded):** Reliability evidence and AI-risk evidence are linked but non-substitutable. A user-journey SLO can trigger change controls, yet a healthy SLO does not approve model behavior. A risk approval permits operation within stated conditions, yet it does not prove that an endpoint is available or a pipeline is fresh. Any coupling between an error budget, quality threshold, and risk response is workload-specific; neither cited source prescribes the combined control rule. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018)

**Illustrative scenario:** The replenishment endpoint meets its availability and latency objectives while outcome-quality evidence becomes uncertain because labels are delayed. The operational policy keeps service telemetry green, marks model evidence inconclusive, stops automated promotion, and routes review to the product and risk owners. No threshold or response cadence is implied outside this scenario.

**Assumptions and trade-offs:** The architecture prefers linked records over a single database, allowing components to evolve independently. This increases integration and identity-management burden. Central policy improves consistency but can become a correlated failure domain. Progressive delivery can limit exposure but adds capacity and comparison complexity. Rich telemetry improves diagnosis but increases cost and privacy risk.

**Failure and recovery:** Common reference-architecture failures include two promotion authorities, mutable references without historical resolution, evidence that arrives after deployment, a rollback target that cannot read present data, and provider telemetry that omits the workload identity. Recovery requires an immutable prior deployment, data compatibility or bypass, named decision authority, user communication, and record reconciliation.

**Forward boundary:** Later chapters own detailed data architecture, feature parity, experiment design, orchestration, registry implementation, deployment strategies, SLO engineering, security controls, cost models, and generative or agentic extensions.

## Production failure case study

**Illustrative scenario:** The entire case is fictional and bounded to the replenishment-ranking workload. It is not a reported company incident, benchmark, or claim about failure frequency.

**Figure `fig-04-failure-propagation` — Semantic data change failure:** [Diagram source](../diagrams/chapter-01/fig-04-failure-propagation.mmd) · [Text alternative](../diagrams/chapter-01/README.md#figure-fig-04-failure-propagation).

The figure traces the path while separating accountability from mechanism. The product workload owns feature semantics, training intent, candidate acceptance, shifted model behavior, fallback behavior, and outcome review. The platform operates admission, feature, training, serving, quarantine, and deployment mechanisms without absorbing those workload decisions. The producer contract owner and incident, release, and risk authority remain independent. Neutral observed-state nodes carry evidence to explicit owner and action nodes rather than assigning responsibility by color.

**Initial architecture:** An upstream inventory service emits a numeric `inventory_age` field. The product workload owns the field meaning, training intent, candidate acceptance, and fallback behavior. Platform mechanisms admit data, execute the workload's feature semantics, train candidates, serve the selected revision, and reconcile deployment. A candidate pipeline validates the schema, evaluates the model, registers an artifact, and promotes through a mutable convenience alias. The serving endpoint reports availability and latency. Product outcomes arrive later.

**Trigger:** The upstream producer changes the field's unit while keeping the name and numeric type. The producer's deployment succeeds, and structural schema validation remains green.

**Propagation:** The online feature path interprets new events under the old semantic contract. The training dataset gradually mixes interpretations. The serving model produces shifted rankings. Exposure changes which products generate future observations, adding direct feedback to the next training data. Direct and hidden feedback are recognized ML system risks. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015)

**Detection:** Endpoint health remains green. A feature-distribution signal changes, but its alert lacks a named response owner. Slice-level product evidence is delayed. A training-serving comparison eventually shows disagreement because the offline replay resolves a different data window. This exposes why unit and end-to-end tests do not establish continuing fitness and why production monitoring must cover system and context change. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) NIST calls for pre-deployment and in-operation testing, production monitoring, and documented response and recovery. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Containment:** The incident owner freezes promotion and CT-triggered candidate admission. The platform quarantine mechanism holds any already-created contaminated candidate with no promotion path, while the workload's candidate-acceptance owner records rejection or hold evidence. The product owner activates pre-approved fallback behavior that bypasses shifted rankings, and the platform fallback-serving mechanism executes that behavior.

The platform team quarantines the incompatible producer revision at the data-admission gate. It preserves the active deployment, input samples permitted by policy, logs, decisions, and alias resolution. The risk owner authorizes either continued operation under the fallback or a risk-authorized safe stop; neither action is inferred from endpoint availability, which remains independent service telemetry.

If risk is unacceptable, operation stops safely until it can be managed, consistent with AI RMF guidance. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Recovery:** Operators first establish the affected producer revision and event-time boundary from retained producer, admission, and provenance records. They normalize only records whose unit can be established. They quarantine or discard an indeterminate interval; when reconstruction is not defensible, they wait for a verified post-fix window rather than label mixed data clean.

The data producer publishes a versioned semantic contract. The product feature owner records explicit unit semantics, and the platform feature mechanism executes them. From normalized data or a verified post-fix window, the product training intent authorizes the platform to build a clean data reference, replay validation, retrain and evaluate a candidate, compare it against the last acceptable artifact, and test serving compatibility.

The workload's candidate-acceptance owner supplies acceptance evidence to the independent approver. The approver writes an approval record that resolves the candidate and evidence. The authorized release workflow writes an immutable desired deployment reference; the deployment controller watches it and alone actuates the serving mechanism.

Recovery is declared only after controller status and workload telemetry record the neutral observed restored state. Immediate service signals and delayed product evidence remain separate after restoration, and the product outcome-review owner decides what the delayed evidence means for workload behavior.

**Prevention - Handbook synthesis (bounded):** The following controls apply only to the fictional incident and its stated assumptions; later chapters select and assess concrete implementations.

- version semantic contracts rather than validating only data types;
- record producer and consumer ownership plus change notification;
- test representative values and invariants at both training and serving boundaries;
- link every candidate to code, configuration, data, feature, environment, evaluation, and prior-model identities;
- separate candidate creation, approval, promotion, and runtime reconciliation;
- attach response owners and actions to data, service, model, and impact alerts;
- preserve a product fallback that does not depend on the affected feature path;
- test rollback with present data and downstream consumers; and
- include endpoint, pipeline, feature, scheduled training, access, and evidence retention in retirement plans.

**Trade-offs:** Stronger contracts can slow producer changes and add version maintenance. Blocking on delayed outcome evidence can reduce release frequency. Retaining replay data improves diagnosis but may conflict with minimization and deletion duties. A fallback reduces impact but costs engineering and can have lower product quality. The architecture decision is not whether to eliminate failure; it is where to detect semantic change, who may contain it, what evidence supports recovery, and how much residual risk is accepted.

**Security and governance implications:** The incident could also be caused by unauthorized change, compromised dependencies, or provider behavior.

**Handbook synthesis (bounded):** Under the scenario's organization-controlled record assumption, select and assess access enforcement, protected logging, integrity verification, backup, and recovery controls for source, build, data, artifact, and control records according to classification and recovery objectives. This is a tailored architecture recommendation rather than a universal effectiveness claim. [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025)

SLSA Build provenance can provide integrity evidence for qualifying packaged artifacts within its Build-track scope, but it does not establish data semantics, model validity, or deployment approval. Signing and provenance must be consumed by trusted verification and admission policy before they can support rejection of an unauthorized packaged artifact.

This combined control boundary joins SLSA artifact provenance and verification to NIST's separate AI-risk decision semantics; none of the sources prescribes a complete ML supply-chain decision system. [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026) [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

NIST treats multiple trustworthiness characteristics as interacting; restoring availability alone does not close safety, privacy, fairness, or accountability questions. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Operational close:** Close the incident only after runtime state, records, alerts, runbooks, product evidence plan, and prevention owners agree. Safe deactivation and decommissioning are part of the lifecycle, not exceptional cleanup. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Forward boundary:** Later chapters select and test semantic-contract enforcement, alert ownership, supply-chain controls, fallback, data recovery, rollout, rollback, and decommissioning implementations. This case establishes only the trigger-to-prevention reasoning and its security, cost, reliability, governance, and operating consequences.

## Architecture decision record exercise

An architecture decision record (ADR) captures a decision, its context and assumptions, considered options, accepted trade-offs, evidence, owner, and review triggers. That definition is handbook synthesis; it is not attributed to an external standard.

**Exercise context - illustrative and bounded:** An organization has three predictive-ML product teams. They need a shared model-evidence and promotion capability across two deployment environments. These quantities exist only for the exercise and are not production evidence. One workload uses sensitive customer data; another has delayed outcome labels; the third runs batch inference.

The organization already operates Kubernetes and source control but has limited capacity for another on-call service. It can select a managed registry and pipeline service, self-host third-party software, build a thin control layer over existing capabilities, or create a custom platform.

**Illustrative constraints and targets:** These values are invented solely to make the exercise testable. Migration must complete within two quarters, and evidence must remain queryable for twelve months. A deployment decision must resolve an immutable artifact and prior rollback target. Recovery from control-plane unavailability must be possible within one hour. Data and model artifacts must remain in approved regions, and provider exit must preserve records and replay instructions.

The exercise intentionally withholds unit prices, run and artifact volumes, growth rate, provider quotations and service limits, staff cost, and the amount of on-call capacity available. The learner must declare provisional envelopes for those inputs, label each estimate, and test at least one lower and one higher case.

The ADR must name the value or provider condition that would reverse the choice. If a hard constraint cannot be evaluated, record a decision blocker or a time-bounded provisional decision instead of inventing evidence.

**Decision prompt:** Write an ADR that selects a composition for tracking, artifact storage, model registration, approval, promotion, and deployment reconciliation. Do not select a tool solely from a feature list. Show which system is authoritative for each record class, who operates each capability, and how a candidate moves from run to approved deployment.

Use this answer skeleton as a completeness check:

- [ ] **1. Decision and owner:** State the selected composition, accountable owner, decision status (`firm`, `provisional`, or `blocked`), and date.
- [ ] **2. Context:** Name the workloads, users, present capabilities, triggering problem, and why a decision is needed now.
- [ ] **3. Hard constraints:** Record data, security, governance, reliability, integration, staffing, cost-envelope, and exit requirements.
- [ ] **4. Assumptions and sensitivity:** Declare change rate, run and artifact volume, workload growth, provider behavior and limits, staffing capacity, unit-cost envelope, and evidence freshness. Identify the values that reverse the choice.
- [ ] **5. Options:** Compare external SaaS, managed cloud, self-hosted third-party, custom, and at least one hybrid composition.
- [ ] **6. Evidence:** Summarize a representative prototype, failure injection, restore or redeploy result, identity and data-path review, lifecycle cost model, and provider export test. Record missing evidence as a blocker.
- [ ] **7. Authority map:** Name canonical source, run, artifact, registry, approval, deployment, incident, and retirement records.
- [ ] **8. Responsibility map:** Map platform, product, risk, security, provider, and incident-command handshakes. Include contracted service limits, security and vulnerability response, change notice, data handling, evidence export, recovery support, portability, and termination duties.
- [ ] **9. Consequences:** Record benefits, new failure domains, operations, security, governance, cost, and migration work.
- [ ] **10. Rejected options:** Tie each rejection to a constraint or tested assumption rather than preference.
- [ ] **11. Exit and recovery:** Describe artifact and metadata export, fallback, restore, replacement interface, and decommissioning.
- [ ] **12. Review triggers:** Include provider change, cost-assumption change, new jurisdiction, new workload type, failed recovery test, control exception, and capability retirement.

**Observable scoring:** A strong answer keeps tracking, artifacts, approval, and deployment state distinct; resolves mutable references to immutable identities; preserves workload accountability; compares lifecycle burden; tests exit; and explains failure handling. Recording a decision blocker, the evidence needed to clear it, and the owner and deadline is a strong signal. It is better architecture than inventing a price, volume, staffing capacity, provider promise, or control result.

A weak answer names a product, calls it the system of record for everything, assumes managed service removes internal responsibility, omits rollback or retirement, or presents an unsupported estimate as evidence.

**Forward boundary:** The exercise tests foundation decisions. Later chapters can substitute concrete registries, orchestrators, policy engines, and serving systems without changing the authority questions.

## Interview questions and evaluation rubric

The interview evaluates architecture reasoning through observable artifacts and decisions. It does not reward title-specific vocabulary or vendor recall. Ask candidates to state assumptions before selecting controls.

**Senior questions:**

1. Draw the system boundary for a predictive model that passes offline evaluation but fails after an upstream semantic data change. Which contracts and signals would you add?
2. Separate candidate creation, approval, promotion, deployment reconciliation, and rollback. Which record is authoritative at each step?
3. Design service, pipeline, data, model, and product signals for an online inference workload. Which owner and response attach to each signal?
4. A mutable registry alias changes during a rollout. How do you preserve auditability and perform a safe rollback?
5. Explain how you would test training-serving parity when exact feature-code reuse is not practical.
6. Given a managed inference capability, map provider, platform, and product-team obligations during an outage.

**Staff questions:**

7. Several teams have different release thresholds. Design one reusable promotion contract without centralizing product acceptance policy.
8. Compare managed, self-hosted, and custom registry or orchestration capabilities. Which lifecycle costs and exit tests can reverse the choice?
9. Design an exception and deprecation model for a golden path. How do you prevent temporary exceptions from becoming permanent platform branches?
10. Build a maturity assessment for low-change batch ML and frequently changing online ML without declaring the higher automation level more mature by definition.
11. A shared feature service creates a correlated failure across workloads. How do you change boundaries, objectives, containment, and migration?
12. Reconcile product ownership of outcomes with platform ownership of delivery contracts and independent risk authority.

**Principal questions:**

13. Define an enterprise control-plane boundary across business units with different jurisdictions and risk tolerances. Which decisions are federated, and which remain enterprise-wide?
14. A strategic provider supplies training, registry, and serving. Develop a concentration-risk and exit strategy that preserves identities, evidence, and transition states.
15. Decide whether to fund a common ML platform, a thin integration contract, or decentralized capability ownership. What portfolio evidence informs the investment?
16. Design a multi-year transition from disconnected registries and deployment scripts to linked authoritative records without stopping product delivery.
17. Explain how reliability policy and AI-risk policy should interact without one dashboard or error budget claiming to prove both.
18. A platform standard reduces local variation but blocks a critical specialized workload. Frame the exception, funding, risk acceptance, and future convergence decision.

**Question-to-evidence map:**

Use the map to make scoring repeatable. Each answer must show the listed signals in the candidate's stated context; adding enterprise detail that is irrelevant to the question earns no extra score.

1. **Semantic change boundary** — Must-have signals: producer and consumer contract; semantic invariant or unit; service, data, model, and outcome signals; containment and recovery path. Relevant dimensions: boundary, assumptions, detection, recovery. Disqualifying omission: treats a type-valid schema as sufficient.
2. **Release authority** — Must-have signals: separate candidate, approval, desired deployment, observed runtime, and rollback records; immutable identities; named decision owner. Relevant dimensions: authority, ownership, recovery. Disqualifying omission: training success authorizes production.
3. **Signal families** — Must-have signals: distinct service, pipeline, data, model, and product measures; active deployment identity; owner and action for each signal. Relevant dimensions: observability, ownership, operations. Disqualifying omission: endpoint health stands in for model or product fitness.
4. **Mutable alias rollback** — Must-have signals: decision-time alias resolution; immutable artifact and configuration; data compatibility check; observed rollback verification. Relevant dimensions: records, failure response, auditability. Disqualifying omission: rollback points to the same mutable alias.
5. **Training-serving parity** — Must-have signals: shared contract or paired implementations; representative values and time boundaries; offline-online comparison; tolerated difference and owner. Relevant dimensions: assumptions, testing, detection. Disqualifying omission: compares only code versions.
6. **Managed inference outage** — Must-have signals: provider service and escalation duties; platform integration and fallback; product impact and communication; incident command. Relevant dimensions: shared responsibility, provider obligations, recovery. Disqualifying omission: transfers workload accountability to the provider.
7. **Reusable promotion contract** — Must-have signals: common evidence interface; workload-owned thresholds; independent approval authority; exception path. Relevant dimensions: reusable contracts, ownership, governance. Disqualifying omission: one central threshold replaces product acceptance.
8. **Sourcing reversal** — Must-have signals: lifecycle cost envelope; operating and security burden; representative prototype or failure test; export and redeploy proof. Relevant dimensions: cost, provider exit, evidence. Disqualifying omission: compares license or compute price alone.
9. **Exception and deprecation** — Must-have signals: named owner; expiry and review trigger; supported transition; retirement or convergence path. Relevant dimensions: exceptions, migration, operations. Disqualifying omission: exception has no expiry or accountable owner.
10. **Contextual maturity** — Must-have signals: risk- and change-adjusted objectives; evidence and recovery posture; manual-control viability; balanced capability dimensions. Relevant dimensions: assumptions, operability, trade-offs. Disqualifying omission: more automation automatically means more maturity.
11. **Correlated feature failure** — Must-have signals: dependency and blast-radius map; independent objectives and signals; containment or bypass; staged migration. Relevant dimensions: correlated risk, recovery, transition. Disqualifying omission: changes the component without a consumer migration path.
12. **Responsibility reconciliation** — Must-have signals: product-outcome owner; platform contract and restoration owner; independent risk decision; explicit incident handshake. Relevant dimensions: ownership, governance, operations. Disqualifying omission: platform availability absorbs product accountability.
13. **Federated control plane** — Must-have signals: enterprise invariants; local decision rights; jurisdiction and risk constraints; escalation and reconciliation model. Relevant dimensions: enterprise boundary, governance, local reversibility. Disqualifying omission: centralizes every decision without a constraint analysis.
14. **Provider concentration and exit** — Must-have signals: dependency inventory; exportable identities and evidence; fallback or parallel capability; sequenced exit test. Relevant dimensions: concentration risk, provider exit, transition states. Disqualifying omission: exports artifact bytes without history or replay semantics.
15. **Platform investment** — Must-have signals: representative workload demand; repeated friction or risk; lifecycle funding and operating model; adoption and retirement measures. Relevant dimensions: portfolio evidence, investment, operations. Disqualifying omission: funds a platform from a vendor-feature comparison.
16. **Record transition** — Must-have signals: canonical fact classes and identity mapping; dual-read or reconciliation state; workload-by-workload migration; rollback and retirement. Relevant dimensions: transition architecture, records, local reversibility. Disqualifying omission: big-bang migration without an operable intermediate state.
17. **Reliability and AI risk** — Must-have signals: separate reliability and risk evidence; named owners and decision paths; explicit interaction trigger; non-substitution rule. Relevant dimensions: governance, reliability, authority. Disqualifying omission: a healthy SLO or error budget approves model behavior.
18. **Specialized-workload exception** — Must-have signals: unmet hard requirement; risk acceptance and funding owner; bounded exception contract; convergence, renewal, or retirement trigger. Relevant dimensions: exception policy, investment, governance, evolution. Disqualifying omission: grants a permanent branch without review.

**Follow-up and partial-answer guidance:** Use one neutral prompt for a missing assumption or artifact; do not supply the design. Then score only the evidence the candidate demonstrated. For this rubric, the role passing levels are Senior 3, Staff 4, and Principal 5.

If the question-specific disqualifying omission remains after that single follow-up, cap the answer one point below the applicable passing level: Senior 2, Staff 3, or Principal 4. Apply the lower of that cap and the score supported by demonstrated evidence.

Senior candidates should identify when a cross-team contract needs Staff escalation; Staff candidates should identify enterprise or jurisdictional decisions that need Principal escalation; Principal candidates should preserve local reversibility rather than inflate every answer into enterprise scope.

Use the following observable rubric for each answer:

| Score | Observable signals |
| --- | --- |
| 1 - Component answer | Names tools or components without system boundary, assumptions, authority, owner, or recovery; treats a successful job or healthy endpoint as sufficient evidence |
| 2 - Local design | Identifies main flow and some tests, but leaves mutable identities, provider obligations, security, cost, or failure response implicit |
| 3 - Operable architecture | States assumptions; separates control, data, artifact, and telemetry flows; names records and owners; covers trade-offs, security, cost, detection, rollback, and runbooks |
| 4 - Cross-team architecture | Adds reusable contracts, exception and deprecation paths, explicit provider operating and recovery obligations, shared-responsibility handshakes, migration, provider exit, and evidence from representative workloads |
| 5 - Enterprise evolution | Frames decision horizon, portfolio dependencies, correlated risk, investment and operating model, transition states, jurisdiction or governance constraints, and review triggers while preserving local reversibility where appropriate |

**Level calibration:** A Senior candidate should consistently reach score 3 for a workload and explain escalation. A Staff candidate should reach score 4 across multiple teams without erasing workload context. A Principal candidate should reach score 5 on enterprise evolution and still reason concretely about records, incidents, and recovery. These thresholds are **illustrative and bounded** to this handbook rubric, not an external hiring standard.

**Red flags:** Unqualified claims that one vendor mode is cheaper or safer; a model registry treated as complete governance; automation equated with maturity; product outcome delegated entirely to the platform; rollback without data compatibility; security reduced to access control; or a strategic plan without transition and retirement.

## Key takeaways

- The unit of production ML architecture is the system and its decision boundaries, not the model file.
- Training creates a candidate; only the named authority can approve production use.
- Use the seven planes to expose authority, interfaces, and failure boundaries—not to prescribe deployment topology.
- Capability maturity is the strength of evidence, control, recovery, and operating contracts appropriate to a workload. Automation is one capability, not a universal destination.
- Canonical records must preserve immutable or versioned identities across release, incident response, rollback, and retirement.
- Assign platform, product, independent authority, and provider obligations before release.
- Compare sourcing modes by workload fit, lifecycle burden, operating ownership, and tested exit.
- Failure readiness means tracing trigger, propagation, detection, containment, recovery, and prevention before release.

**Handbook synthesis (bounded):** These eight rules are the chapter's decision synthesis, not a standard or a combined architecture prescribed by any one source. Their evidence and applicability boundaries remain at the earlier points of proof and in the [claim-coverage appendix](#glossary-additions-and-authoritative-references).

## Glossary additions and authoritative references

The controlled definitions for MLOps, ML system, control plane, data plane, training plane, serving plane, model registry, artifact store, lineage, reproducibility, CT, SLI, SLO, and ADR are maintained in [the handbook glossary](../GLOSSARY.md#controlled-terms). The handbook-specific plane, record, maturity, responsibility, and role-scope definitions in this chapter remain bounded synthesis until editorial and technical review approve them.

All external factual statements cite stable keys in [the authoritative bibliography](../sources/references.md#authoritative-bibliography). Product behavior is version-scoped. Vendor sources support the named vendor's documented model or position, not cross-vendor superiority. NIST AI RMF claims are pinned to version 1.0. As observed on 2026-08-23, the NIST program page stated that AI RMF 1.0 was under revision; this status must be rechecked before publication or by the ledger review deadline. [`NIST-AIRMFSTATUS-2026`](../sources/references.md#nist-airmfstatus-2026)

**Claim-coverage appendix:** Claim identifiers stay out of the main prose except in this audit map. Each listed range refers to a verified or explicitly qualified row in `claim-ledger.csv`.

- [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015): CH01-C001, CH01-C003-C005, CH01-C013.
- [`BRECK-MLTESTSCORE-2017`](../sources/references.md#breck-mltestscore-2017): CH01-C002, CH01-C006-C010.
- [`GOOGLE-RULESML-2025`](../sources/references.md#google-rulesml-2025): CH01-C011-C012.
- [`KUBERNETES-COMPONENTS-2026`](../sources/references.md#kubernetes-components-2026): CH01-C014-C015.
- [`KUBERNETES-CONTROLLERS-2024`](../sources/references.md#kubernetes-controllers-2024): CH01-C016 and qualified synthesis CH01-C056.
- [`KUBERNETES-WORKLOADS-2026`](../sources/references.md#kubernetes-workloads-2026): CH01-C017.
- [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026): CH01-C018-C019 and qualified synthesis CH01-C057.
- [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026): CH01-C020-C021 and qualified synthesis CH01-C057.
- [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023): CH01-C022-C029, CH01-C033, CH01-C037, CH01-C042, and qualified syntheses CH01-C058-C061.
- [`NIST-SP80053R5-2025`](../sources/references.md#nist-sp80053r5-2025): CH01-C066-C068 and qualified synthesis CH01-C070.
- [`NIST-AIRMFPLAYBOOK-2023`](../sources/references.md#nist-airmfplaybook-2023): CH01-C030.
- [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024): CH01-C031-C032, CH01-C038, CH01-C043-C044, and the Google Cloud portions of qualified synthesis CH01-C059-C060.
- [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018): CH01-C034-C036 and the reliability portion of qualified synthesis CH01-C058.
- [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026): CH01-C039-C041 and qualified syntheses CH01-C061 and CH01-C071.
- [`SLSA-VERIFICATION-2026`](../sources/references.md#slsa-verification-2026): CH01-C069 and qualified synthesis CH01-C071.
- [`AWS-MLDESIGN-2025`](../sources/references.md#aws-mldesign-2025): CH01-C045.
- [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025): CH01-C053 and qualified synthesis CH01-C063.
- [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025): CH01-C054 and qualified syntheses CH01-C063 and CH01-C072.
- [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023): CH01-C046-C047, CH01-C055, and qualified syntheses CH01-C062-C064 and CH01-C072.
- [`TEAMTOPOLOGIES-TVP-2019`](../sources/references.md#teamtopologies-tvp-2019): CH01-C048.
- [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026): CH01-C052 and qualified synthesis CH01-C063.
- [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025): CH01-C049-C051 and qualified syntheses CH01-C062, CH01-C064, and CH01-C072.
- [`NIST-AIRMFSTATUS-2026`](../sources/references.md#nist-airmfstatus-2026): CH01-C065.

The chapter does not rely on bibliography entries that are absent from the coverage map. Applicability limits, source dates, versions, and review deadlines remain authoritative in the claim ledger and bibliography.

## Changelog

### 2026-08-23

- Closed the focused editorial rereview findings by making the takeaways concise, restoring the exact H3 contract, and defining deterministic role-level scoring caps for unresolved question-specific omissions.
- Closed Task 8 technical rereview findings R1 and R2 by making Figure 1 use a passive desired-state record and deployment-controller-only actuation, and by separating Figure 4 platform execution mechanisms, product workload accountability, neutral observed facts, producer ownership, and independent decision authority.
- Clarified Stage 3 as an authorized release workflow that writes desired state plus a deployment controller that alone actuates runtime; separately gated identities and permissions preserve those logical authorities when one product implements both.
- Corrected Task 8 editorial and accessibility findings with in-chapter navigation, point-of-use diagram alternatives, linear responsibility and sourcing comparisons, consolidated forward boundaries, a decision-complete ADR exercise, and question-level evaluation evidence.
- Corrected Task 8 technical findings by separating request from release and risk authority; artifact bytes from control metadata; passive records from controller actuation; CI/CD from CT and model release; and platform mechanisms from workload accountability.
- Added explicit provider obligations and failure-containment and recovery paths through producer and candidate quarantine, fallback or safe stop, affected-interval treatment, approval, immutable desired state, controller reconciliation, and observed restoration.
- Pinned Kubernetes product behavior to v1.36 and its immutable official documentation revisions.
- Inventoried security and normative prose; replaced unbounded effectiveness language with tailored-control assumptions; added NIST SP 800-53 and SLSA verification evidence; and mapped CH01-C066 through CH01-C071 at point of use.
- Added the qualified provider-contract evidence boundary CH01-C072 for directly established service, support, change, observability, audit, and exit obligations.
- Created the complete Chapter 1 prose with the canonical section sequence.
- Added the seven-plane architecture model, capability maturity model, system-of-record classes, responsibility contract, sourcing framework, role-scope model, lifecycle flow, bounded failure case, ADR exercise, interview questions, and observable rubric.
- Mapped external factual claims to the verified Chapter 1 evidence set and labeled cross-source architectural judgments as bounded handbook synthesis.
- Addressed Task 6 review findings I1, I2, and M1 by labeling repeated qualified syntheses at point of use, reconciling appendix mappings to exact ledger source keys, and adding the role-scope forward boundary.
- Audited all Chapter 1 Markdown targets and anchors, glossary navigation, acronym first use, and plain-language forward boundaries for Task 7 integration; no technical claim or qualified-synthesis boundary changed.
