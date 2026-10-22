# MLOps Architecture Foundations: From ML Lifecycle to Enterprise Platform Strategy

## Reader outcomes and prerequisites

**Handbook synthesis (bounded):** A production machine learning (ML) service is not a model wrapped in an endpoint. In this chapter, its boundary is the chain of data contracts, code, configuration, training runs, evaluation evidence, artifacts, approvals, deployment state, runtime dependencies, user outcomes, and feedback. Machine learning operations (MLOps) names the operating discipline for that chain. This boundary follows the production-system framing in the verified evidence set and is limited here to predictive ML; generative and agentic extensions are deferred. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

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

**Security, governance, reliability, and cost:** Access controls and provenance reduce unauthorized substitution but do not prove data suitability. Governance identifies who may accept residual risk. Reliability defines user-facing service behavior. Cost includes evidence retention, validation compute, telemetry, and recovery drills, not only training and serving. The architecture planes and record classes below make these concerns assignable. Later chapters will deepen data contracts, evaluation, and incident practice.

## ML lifecycle and operational feedback loops

Google's practitioner guidance defines an ML pipeline as infrastructure that gathers data, creates training data, trains models, and exports models to production. It treats deployment as iterative and recommends repeated launches, model-delta measurement, and training-serving skew monitoring. [`GOOGLE-RULESML-2025`](../sources/references.md#google-rulesml-2025) Google's predictive-ML architecture guidance adds data and schema validation, comparison against a baseline, segment evaluation, compatibility testing, pipeline metadata, and production monitoring. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

[Figure `fig-01-ml-lifecycle`: ML lifecycle and operational feedback loops](../diagrams/chapter-01/fig-01-ml-lifecycle.mmd) shows four kinds of movement that must not be collapsed:

- **data flow:** events and validated datasets move toward feature computation and training;
- **artifact flow:** code packages, evaluation bundles, and model artifacts move toward approval and serving;
- **control flow:** policies, triggers, approvals, desired deployment references, and rollback commands direct work;
- **telemetry and outcome flow:** service signals, data signals, model behavior, incidents, and product outcomes return to operators and future training.

**Handbook synthesis (bounded):** A useful lifecycle contract is:

`product event -> captured data -> validated data reference -> training run -> evaluated candidate -> approval decision -> immutable deployment reference -> serving workload -> prediction or action -> telemetry and outcome -> review, retraining, rollback, or retirement`

This sequence is a reasoning aid, not a required physical topology. Batch scoring can replace online serving; human review can sit before an action; an embedded model may have an intermittent telemetry path; and a low-change workload may retain manual transitions.

Feedback makes the loop architectural rather than decorative. Direct feedback occurs when model decisions affect which future data is selected for training. Hidden feedback occurs when separate systems influence each other indirectly through the world. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) In the replenishment scenario, ranked products receive more exposure and therefore produce more observed outcomes. The absence of an outcome for an unranked product is not neutral evidence.

NIST AI RMF 1.0 treats testing, evaluation, verification, and validation as continuing into operation through monitoring, incident tracking, updates, and recalibration. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Google's predictive-ML example separates training triggers and validation from reviewer approval and production promotion. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) **Handbook synthesis (bounded):** A continuous training (CT) trigger may create a candidate while production promotion remains a separate, policy-governed decision. This combined architecture rule is derived from the two cited boundaries; neither Google Cloud nor NIST individually prescribes the complete approval design. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

> **Decision:** The product risk owner and technical release owner define whether a trigger may train, evaluate, promote, roll back, or only request review.
>
> **Assumptions:** The trigger policy is workload-specific, resolves immutable identities, and records its decision evidence.
>
> **Trade-off:** More automation shortens repetitive handling and can make evidence collection consistent; it also increases the impact of a faulty policy or shared dependency.

**Failure modes:** The loop can retrain on model-influenced labels, accept stale outcomes, equate job success with model acceptance, or turn a noisy alert into repeated candidate creation. Delayed or missing ground truth can leave proxy signals green while product outcomes deteriorate.

**Security and governance:** Identity, intended-use boundaries, data rights, third-party controls, approval authority, and safe retirement remain in force throughout the loop. NIST calls for inventories, monitoring, incident practices, third-party risk policies, and safe decommissioning. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Reliability and cost:** Separate user-visible service health from pipeline freshness, data fitness, model behavior, and governance signals. Each family has different owners and actions. More frequent training can increase compute and review burden without improving a low-change workload. Google's guidance explicitly allows manual delivery where models change infrequently and advises gradual automation. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

Later chapters own detailed trigger design, feature parity, evaluation, rollout, monitoring, and feedback-bias mitigation.

## Architecture planes

Planes are responsibility and authority boundaries, not mandatory clusters, networks, teams, or products. One service may implement several planes; one plane may span many services. [Figure `fig-02-architecture-planes`: Seven architecture planes](../diagrams/chapter-01/fig-02-architecture-planes.mmd) names the flows among them.

Kubernetes provides the sourced analogy, not the enterprise ML decomposition. In the reviewed Kubernetes architecture, the application programming interface (API) server exposes the cluster API, etcd stores API data, and schedulers and controllers perform control-plane functions; worker-node components execute workloads. [`KUBERNETES-COMPONENTS-2026`](../sources/references.md#kubernetes-components-2026) Controllers observe state and move it toward declared intent, while higher-level workload resources maintain specified Pods. [`KUBERNETES-CONTROLLERS-2024`](../sources/references.md#kubernetes-controllers-2024) [`KUBERNETES-WORKLOADS-2026`](../sources/references.md#kubernetes-workloads-2026)

### Control plane

**Handbook synthesis (bounded):** The ML control plane accepts declared intent, writes authoritative desired state, invokes policy, schedules reconciliation, records observed status, and issues corrective action. It can coordinate training requests, promotion decisions, deployment references, rollback, and retirement. The transferable pattern is `declared intent -> authoritative state -> reconciliation -> observed status -> corrective action`; Kubernetes supports the analogy but does not define a complete enterprise ML control plane. [`KUBERNETES-CONTROLLERS-2024`](../sources/references.md#kubernetes-controllers-2024)

In the replenishment workload, the control plane receives a promotion request for a candidate digest, verifies required evidence, records approval, and declares the serving revision. Its primary failure mode is authority confusion: two systems can both appear able to promote. Centralizing authority simplifies audit and reconciliation but can create a high-impact dependency. Security requires strong authentication, scoped authorization, tamper-evident decision records, and emergency access procedures. Cost concentrates in control-plane reliability, integration, and policy maintenance. Later chapters own concrete controllers and policy engines.

### Data plane

**Handbook synthesis (bounded):** The data plane carries workload data under declared policy: raw events, validated datasets, online features, batch features, predictions, and outcome observations. It owns movement and enforcement at the data path, not the truth of product semantics by itself.

The replenishment data plane moves inventory events into validated storage and feature views. A useful contract includes schema, semantic invariants, event-time behavior, identity, classification, retention, deletion, and consumer notification. The trade-off is between reusable shared paths and workload-specific semantics. Failure modes include silent unit changes, skew, late data, unauthorized access, and feedback contamination. Encryption, identity, minimization, and access logging protect the path, while product and governance owners still decide suitability and lawful use. Storage, transfer, validation, and replay dominate cost. Later chapters own data and feature architecture.

### Training plane

**Handbook synthesis (bounded):** The training plane transforms versioned code, configuration, and data references into candidate artifacts plus run and evaluation evidence. A successful training job creates a candidate, not an approval.

In the scenario, a training request resolves code, environment, feature definitions, data window, and prior-model pointer. It emits a model digest, metrics, slice results, logs, and lineage references. The trade-off is reproducibility versus execution flexibility and cost. Exact identity may be infeasible for some workloads; the required tolerance should be explicit. Failure modes include unpinned dependencies, non-replayable data, leakage, resource exhaustion, and evidence published after a partial failure. Isolation, secret scoping, dependency integrity, and artifact signing reduce attack paths. Compute efficiency must be measured against diagnosis and recovery needs. Later chapters own distributed training, accelerators, and experiment design.

### Serving plane

**Handbook synthesis (bounded):** The serving plane resolves an approved immutable model identity and returns batch, streaming, or online outputs with runtime telemetry. It enforces the deployment contract but does not decide whether the model's product behavior remains acceptable.

The replenishment service loads the approved digest and records its runtime revision. A mutable convenience alias may select a version, but rollback evidence should preserve the resolved version. In MLflow 3.15.1, aliases are mutable named references and fixed stages have been deprecated since version 2.9.0. [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026) Trade-offs include latency against batching, utilization against isolation, and progressive exposure against operational complexity. Failure modes include incompatible runtime dependencies, alias races, stale caches, partial rollout, and silent fallback. Security includes artifact verification, least privilege, network policy, and abuse controls. Later chapters own online, batch, streaming, and specialized inference patterns.

### Observability plane

**Handbook synthesis (bounded):** The observability plane preserves separate views of service health, pipeline and data health, model behavior, and governance or product impact. It links signals to the exact data, artifact, deployment, and decision identities active at observation time.

For the replenishment workload, endpoint availability cannot substitute for feature freshness or ranking acceptance. Google defines a service-level indicator (SLI) as a measurement of service delivered to users and a service-level objective (SLO) as a target reliability level. Candidate SLI types include availability, latency, quality, pipeline freshness, pipeline correctness, pipeline coverage, and storage durability. [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018) The trade-off is signal coverage against cost, noise, and sensitive-data exposure. Failure modes include aggregate dashboards hiding affected slices, missing deployment labels, alert loops without an owner, and delayed ground truth. Later chapters own telemetry design, drift analysis, and SLO implementation.

### Security and governance plane

**Handbook synthesis (bounded):** The security and governance plane expresses intended use, control tier, identity policy, evidence requirements, approval authority, third-party controls, residual risk, incident decisions, and retirement. It supplies policy decisions to other planes and receives evidence back; it is not a document portal detached from execution.

NIST AI RMF 1.0 is voluntary, rights-preserving, non-sector-specific, and use-case agnostic. It organizes outcomes into Govern, Map, Measure, and Manage, with Govern cross-cutting, and states that these functions are not a checklist or required sequence. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) The NIST Playbook suggests risk scales, oversight tiers, and approval, conditional-approval, or disapproval paths as optional actions rather than mandates. [`NIST-AIRMFPLAYBOOK-2023`](../sources/references.md#nist-airmfplaybook-2023)

In the scenario, this plane records intended use, approvers, evaluation expectations, permitted data, deployment constraints, and stop conditions. Failure modes include policy that cannot be enforced, an exception without expiry, missing third-party contingency, and no decommissioning owner. Strong control depth improves accountability but adds review and evidence cost. Applicable legal duties remain a separate, jurisdiction-specific analysis. Later chapters own threat modeling, privacy, compliance, and AI-risk implementation.

### Platform experience plane

**Handbook synthesis (bounded):** The platform experience plane turns reusable capabilities into supported journeys through APIs, command-line interfaces, templates, documentation, policy feedback, service expectations, and escalation paths. It owns the contract and user experience even when another internal team or external provider implements a capability.

The Cloud Native Computing Foundation (CNCF) defines a cloud-native platform as an integrated collection of capabilities presented around user needs and assigns platform teams user research, roadmap planning, and interfaces, while capability implementation may sit elsewhere. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) In the scenario, the experience plane offers a supported route from training request to evidence-backed promotion. The trade-off is standardization against specialized needs. Failure modes include a portal that hides unsupported provider behavior, a golden path with no recovery contract, and abstractions that prevent diagnosis. Security guardrails must be visible and actionable. Cost includes product discovery, support, adoption, deprecation, and migration. Later chapters own developer experience and platform product management.

The seven-plane split prevents a familiar ownership error: declaring that a registry, pipeline, cluster, or dashboard is the MLOps platform. Each is a capability inside a larger decision system.

## MLOps capability and maturity model

The model below is **Handbook synthesis (bounded)**. It combines automation capability, balanced production-readiness evidence, governance, reliability, and platform operating practice. It is not a standard, compliance score, or fixed sequence. A low-change workload can remain deliberately manual if its controls, evidence, and recovery posture fit its risk. Google's predictive-ML guidance separates manual delivery, automated ML pipelines, and automated continuous integration and continuous delivery (CI/CD) for pipeline changes, and allows manual delivery when change is infrequent. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

The ML Test Score contributes a useful coverage warning. It defines 28 checks across features and data, model development, ML infrastructure, and monitoring; it gives partial credit for documented manual execution, full credit for repeated automation, and uses the minimum of the four area totals so strength in one area cannot hide weakness in another. [`BRECK-MLTESTSCORE-2017`](../sources/references.md#breck-mltestscore-2017) Its dominant context was supervised learning with repeated training and low-latency serving, and its study applied the rubric through structured interviews with 36 Google teams. It should therefore be used as a diagnostic taxonomy within that boundary, not as a universal maturity standard. [`BRECK-MLTESTSCORE-2017`](../sources/references.md#breck-mltestscore-2017)

### Stage 0: Explicit manual control

The workload has named owners, version identities, a documented release checklist, approval evidence, rollback or bypass instructions, and an inventory entry. Execution may be manual. The maturity test is whether a second operator can identify what changed, who approved it, what is running, and how to recover.

**Illustrative scenario:** The replenishment team trains infrequently and promotes through a reviewed runbook. This is bounded to the teaching workload. The trade-off is operator effort and slower repetition in exchange for lower automation investment. Failure modes are skipped steps, stale evidence, and person-dependent recovery. Security requires separation of ordinary and emergency access. Cost includes review time and rehearsal. The next investment should target the manual transition with the largest release or recovery risk, not automate every step.

### Stage 1: Repeatable evidence

Source, data, run, artifact, evaluation, approval, deployment, and rollback identities are captured consistently. Tests are repeatable; manual execution is documented; telemetry names the active deployment. The operational question moves from "what happened?" to "did the recorded evidence satisfy the declared policy?"

The trade-off is metadata and retention overhead. Failure modes include collecting records without linking them, making dashboards canonical, and retaining sensitive evidence beyond its purpose. Governance defines retention and reviewer independence; operations test record restoration. Later chapters own lineage schemas and evidence storage.

### Stage 2: Automated candidate pipeline

Data and schema validation, training, evaluation, compatibility checks, metadata capture, and candidate registration run as a pipeline. Google's predictive-ML pattern includes these capabilities and separates them from promotion. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

The trade-off is faster, more consistent candidate creation against a larger shared failure radius. A faulty common component can produce many invalid candidates. Security requires isolated execution and verified dependencies. Cost control needs workload-aware scheduling and evidence-retention policy. Recovery cancels or quarantines candidates without changing production. Later chapters own pipeline orchestration and test design.

### Stage 3: Governed continuous delivery

CI/CD validates pipeline changes, resolves immutable artifacts, enforces approval policy, deploys progressively where suitable, measures user and system signals, and preserves rollback evidence. **Handbook synthesis (bounded):** A CT event may create a candidate for this path, but promotion remains a distinct, workload-specific policy decision; neither cited source individually prescribes the combined approval architecture. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

The trade-off is release speed against policy and controller complexity. Failure modes include a policy bug that authorizes broad rollout, a shared control-plane outage, or rollback that restores service but not data compatibility. NIST calls for pre-deployment and in-operation testing, production monitoring, and documented response and recovery. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Cost includes resilient control-plane operation, canary capacity, and on-call readiness. Later chapters own deployment controllers and release strategies.

### Stage 4: Portfolio platform

Reusable journeys serve multiple workloads through explicit contracts, optional capabilities, exception and deprecation paths, provider abstraction where justified, shared evidence interfaces, and portfolio-level risk and cost review. CNCF recommends platform-as-product, self-service, optional composition, and a thin integration layer for cloud-native delivery. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

The trade-off is organizational leverage against abstraction, migration, and support burden. Failure modes include standardizing a local preference, hiding provider limits, funding build work without operations, and accumulating permanent exceptions. Security and governance set shared guardrails while product teams retain workload accountability. Portfolio cost includes platform product work, provider concentration, adoption support, and retirement. Later chapters own multi-tenancy, capacity, financial operations (FinOps), and platform evolution.

NIST AI RMF's Govern, Map, Measure, and Manage functions can be used to test every stage, but the framework explicitly does not define a checklist or execution order. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Amazon Web Services (AWS) guidance also joins ownership and automation with protection, resiliency, reusability, reproducibility, resource trade-offs, cost awareness, and continuous improvement; that is AWS practitioner guidance, not a cross-vendor standard. [`AWS-MLDESIGN-2025`](../sources/references.md#aws-mldesign-2025)

## System-of-record boundaries

During an incident, "the registry says champion" is not enough. An operator needs the exact artifact digest, source run, data reference, evaluation bundle, approval decision, deployment revision, runtime configuration, observed signals, and rollback target that applied at the relevant time.

[Figure `fig-03-systems-of-record`: Linked systems of record](../diagrams/chapter-01/fig-03-systems-of-record.mmd) distinguishes authoritative record classes from catalogs and dashboards. The classification below is **Handbook synthesis (bounded)**: each fact class should have a canonical record joined through immutable or versioned identities, while search, catalog, and dashboard views remain derived. NIST and Google Cloud support traceability outcomes but do not prescribe this schema. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)

Google Cloud's predictive-ML metadata example records pipeline and component versions, execution context, parameters, produced artifacts, prior-model pointers, and evaluation metrics. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) The example supports linked lineage evidence within that documented pattern; it does not establish one enterprise record schema.

### Source and configuration records

These records identify code revisions, pipeline definitions, dependency locks, environment descriptions, policy versions, infrastructure configuration, and feature logic. The authority is usually source control plus approved configuration state, not a copied value in a run dashboard.

The replenishment workload links its training and serving revisions to source and configuration identities. The trade-off is strict immutability against emergency change speed. Failure modes include uncommitted runtime edits and secret values copied into evidence. Security requires protected change paths and secret references rather than secret contents. Cost arises from retention, review, and configuration reconciliation. Later chapters own source and infrastructure controls.

### Data and feature records

These records identify source datasets or event boundaries, schema and semantic contracts, feature definitions, time windows, classifications, access decisions, retention, and deletion state. They distinguish a data pointer from a stored copy and state the reproducibility tolerance.

The scenario records the exact inventory-event boundary and feature definition used for training. The trade-off is replayability against storage, privacy, and staleness. Failure modes include an immutable identifier pointing to mutable content, late-arriving data changing a window, and deletion obligations not propagating. Security and governance decide access and retention. Later chapters own dataset versioning and feature stores.

### Run and artifact records

In MLflow 3.15.1, a run records parameters, metrics, timing, and output artifacts; its backend store persists run metadata while an artifact store holds large outputs such as model weights and data files. [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026) **Handbook synthesis (bounded):** Tracking metadata, artifact storage, model registration, and deployment state are separate record classes even when one product presents several together. The MLflow sources describe product behavior but do not prescribe this enterprise authority boundary. [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026) [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026)

The replenishment run record links inputs, execution context, outputs, logs, and evaluation evidence. The artifact record identifies model and package bytes by immutable digest. Trade-offs include rich evidence against storage cost and sensitive-data exposure. Failure modes include successful metadata publication with missing artifacts, artifacts overwritten at a stable path, and retention mismatch. Access controls, integrity checks, and restore tests are required. Later chapters own experiment tracking and artifact storage.

### Model and approval records

In MLflow 3.15.1, the registry workflow supports registered models, versions, aliases, tags, descriptions, source-run information, and creation timestamps. [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026) **Handbook synthesis (bounded):** Those capabilities do not make a registry the full governance system of record; that authority boundary remains workload- and organization-specific. [`MLFLOW-TRACKING-2026`](../sources/references.md#mlflow-tracking-2026) [`MLFLOW-REGISTRY-2026`](../sources/references.md#mlflow-registry-2026)

The model record describes candidate and version identity; the approval record names the decision, policy version, evidence set, approver, conditions, expiry or review trigger, and residual risk. A mutable alias is useful for discovery or routing, but an audit record resolves it to the immutable version observed at decision time. The trade-off is convenience against historical certainty. Failure modes include alias reassignment racing deployment and approval represented only by a tag. Later chapters own registry and approval workflows.

### Deployment and runtime records

These records identify desired deployment state, resolved artifact, environment, runtime and configuration versions, rollout state, active endpoints or jobs, traffic allocation, observed status, and rollback target. They answer "what was intended?" and "what was actually active?"

The scenario ties each prediction log to a deployment identity. The trade-off is telemetry cardinality and storage against diagnosis. Failure modes include partial rollout, configuration drift, stale routing, and rollback to an artifact incompatible with present data. Security requires signed artifacts, scoped deploy authority, and auditable emergency actions. Reliability requires reconciliation and tested recovery. Later chapters own serving and release state.

### Risk, incident, and retirement records

NIST AI RMF 1.0 calls for an AI-system inventory, periodic review, third-party risk policy, incident practices, and safe decommissioning. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) These records capture intended and prohibited use, affected context, control tier, third-party components, risk decisions, exceptions, incidents, recovery actions, dependents, retention duties, and deactivation.

The scenario links an incident to the affected deployment, data contract, decisions, and recovery evidence. The trade-off is audit depth against sensitive context and operational burden. Failure modes include an inventory that is not connected to runtime, an exception without review, and retirement that leaves scheduled training active. Later chapters own governance operations and decommissioning.

Supply-chain Levels for Software Artifacts (SLSA) v1.2 Build provenance binds an output package digest to how it was produced; higher Build levels add authenticity, control-plane-generated provenance, hosted builds, and isolation requirements. Its Build track is scoped to software package production and can omit some resolved dependencies. [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026) **Handbook synthesis (bounded):** SLSA Build provenance is one artifact-integrity record. It does not establish dataset fitness, model validity, approval legitimacy, or complete ML lineage. This combined boundary joins SLSA's artifact scope to NIST's separate AI-risk evidence and decision semantics; neither source prescribes a complete ML lineage authority. [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

## Platform and product-team responsibilities

A failed handoff often starts with two plausible statements: "the platform owns production" and "the product team owns the model." Neither identifies who decides whether an evaluation is sufficient, who owns endpoint restoration, who accepts product risk, who communicates a provider incident, or who retires dependent pipelines.

CNCF's cloud-native platform guidance frames a platform as capabilities presented around user needs and assigns the platform team user research, roadmap planning, and interfaces, while implementation may reside with another internal team or managed provider. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) Microsoft frames a workload as application resources, custom code, AI models, data, and supporting infrastructure that achieve a business outcome; workload teams focus on that outcome while centralized teams provide shared services, guidance, and guardrails. [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

The following model is **Handbook synthesis (bounded)**. It is a starting responsibility contract, not a universal organization chart.

| Decision boundary | Platform team | Product or workload team | Shared or independent authority |
| --- | --- | --- | --- |
| Supported journey | Own interface, documentation, onboarding, support, deprecation, and platform service expectations | Select a supported path or justify an exception | Agree adoption criteria, exception expiry, and migration |
| Data and model logic | Provide hooks, identity, storage interfaces, and baseline controls | Own feature logic, training intent, acceptance criteria, and product behavior | Governance or independent reviewers may approve defined risk evidence |
| Delivery | Operate reusable orchestration, policy enforcement points, artifact interfaces, and deployment mechanisms | Supply workload configuration, evidence, release intent, and rollback conditions | Release authority resolves conflicts and records the decision |
| Reliability | Own platform dependency objectives, telemetry, runbooks, breaking-change notice, and restoration | Own end-to-end workload objectives, application telemetry, user-impact response, and workload runbooks | Incident command and escalation are named before release |
| Security and governance | Provide organization guardrails, identity integration, audit export, and approved capability catalog | Classify data, assess workload and dependency risk, and operate within approved use | Security, legal, governance, or risk owners retain their decision authority |
| Provider dependency | Operate provider integration and service escalation | Own workload fallback behavior and product communication inputs | Contract owner, platform, and product coordinate contingency and exit |
| Product outcome | Measure platform adoption and capability health | Own business outcome, user experience, model behavior, and outcome measurement | A platform limitation can block release but does not absorb product accountability |

NIST calls for documented roles and communication lines plus executive responsibility for development and deployment risk decisions. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) Google's SLO approach calls for stakeholder-approved objectives, an empowered owner, a written error-budget policy, and refinement. [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018) Microsoft also advises making compliance, observability, performance, support, budget, and change-control expectations explicit in shared-responsibility discussions. [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

**Illustrative scenario:** The replenishment endpoint meets the platform availability objective, but a product acceptance signal breaches its bound. The product owner decides whether workload behavior remains acceptable; the platform keeps the deployment and rollback mechanisms available; the risk authority decides whether operating conditions remain permitted. If the shared deployment API breaks its published contract, the platform owns capability restoration. If a managed provider causes the failure, internal owners still coordinate containment, escalation, recovery, and communication.

**Assumptions:** Each decision has one accountable owner even when several teams execute work. Small organizations may assign several decisions to one person without merging the records.

**Trade-offs and failure modes:** Centralization can make controls consistent but can separate decisions from workload context. Decentralization can improve context but duplicate controls and create uneven evidence. A golden path can reduce cognitive load yet become a bottleneck if exceptions lack an owner. Security and governance need independent authority where required; product teams cannot delegate user impact to a platform abstraction. Cost allocation must include platform support and workload-specific operations.

Team Topologies advises a thinnest viable platform no thicker than needed and notes that it can be a page naming approved cloud services plus usage guidance. [`TEAMTOPOLOGIES-TVP-2019`](../sources/references.md#teamtopologies-tvp-2019) Start with the smallest contract that closes an observed responsibility or delivery gap. Later chapters own detailed team topology, service ownership, and operating models.

## Build, buy, and managed-service decisions

"Build versus buy" hides at least four modes: external software as a service (SaaS) or model API, managed cloud capability, self-hosted third-party software, and custom implementation. A platform can compose all four. Evaluate each capability separately rather than choosing one mode for the whole platform.

Microsoft frames SaaS, platform as a service (PaaS), and custom AI choices through data control, customization, upkeep, performance, expertise, security, and compliance. [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026) AWS recommends comparing custom and pre-trained models using data, task specificity, performance, expertise, development time, infrastructure, security, and long-term maintenance. [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025) These are vendor comparison factors, not universal selection outcomes.

### Decision dimension: workload and differentiation

State the product outcome, acceptance envelope, change rate, data sensitivity, latency or freshness profile, availability and recovery objectives, integration surfaces, and evidence required for release. Then classify whether the capability differentiates the product or supplies common infrastructure.

In the scenario, ranking policy is workload-specific while artifact storage is a common capability. Building both would absorb different long-term obligations. The failure mode is declaring a capability differentiating because the team has already customized it. The decision should be revisited when requirements or provider capabilities change. Later chapters own workload-specific requirement methods.

### Decision dimension: control, security, and governance

Compare data location, identity, network boundaries, customization, auditability, supply-chain evidence, third-party controls, support terms, and applicable compliance constraints. NIST calls for policies, monitoring, controls, and contingency processes for third-party data, software, AI systems, and pretrained models. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

Managed service does not mean managed workload risk; custom implementation does not imply compliance. The failure mode is treating an implementation label as control evidence. Security and governance reviewers should test actual data paths, permissions, artifacts, contracts, and incident processes. Later chapters own control assessment.

### Decision dimension: lifecycle economics and operations

Model acquisition, integration, identity and network work, data movement, migration, upgrades, patches, capacity, observability, on-call, support, incident coordination, training, evidence retention, and retirement. AWS identifies infrastructure, personnel, maintenance, scaling, upgrades, utilization, and pricing model as managed-service cost inputs but does not establish a workload-neutral cost result. [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025)

The failure mode is comparing license or compute price while excluding operations and exit. A managed service can remove some toil and add provider dependency; self-hosting can increase control and add staffing and recovery burden. Sensitivity analysis should expose which assumptions reverse the decision. Later chapters own cost modeling and capacity engineering.

### Decision dimension: portability and exit

Require exportable artifacts, metadata, logs, and decision evidence; stable interfaces; a dependency inventory; tested restore or redeploy; contractual termination; and a replacement path. CNCF recommends a thin platform layer over capability providers with optional and composable offerings in its cloud-native delivery scope. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

Abstraction has a cost. A thin interface can preserve options, but a lowest-common-denominator layer can hide valuable provider behavior and obstruct diagnosis. The failure mode is an exit plan that exports bytes without semantics, history, or replay capability. Later chapters own migration and portability patterns.

### Decision dimension: evidence and review triggers

Prototype the assumption with the highest decision risk using representative workload conditions. Record the owner, source evidence, accepted trade-offs, rejected modes, exception, review trigger, and retirement condition in an architecture decision record (ADR).

The mode comparison is **Handbook synthesis (bounded)**. It compares workload requirements, lifecycle burden, operating ownership, and exit evidence; none of the cited vendor or platform sources prescribes the combined decision rule. [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025) [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025) [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026) [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)

| Mode | Select when local evidence shows | Burden to expose | Exit evidence |
| --- | --- | --- | --- |
| External SaaS or model API | Behavior and contractual controls fit a non-differentiating need | Provider concentration, opaque change, data handling, unit economics, quotas, and regions | Exportable data and logs, substitutable interface, fallback, and termination plan |
| Managed cloud capability | Removed operations justify service coupling and constraints | Shared-responsibility gaps, service limits, pricing, regions, and constrained customization | Artifact and metadata export, dependency inventory, and tested redeploy |
| Self-hosted third-party software | Control, portability, extension, or deployment constraints justify internal operation | Upgrades, patches, security response, specialized staffing, scaling, and on-call | Reproducible deployment, backups, versioned configuration, upgrade path, and support contingency |
| Custom implementation | A material differentiator or hard requirement is unmet elsewhere | Product roadmap, reliability, security, adoption, opportunity cost, and succession | Stable interfaces, maintained documentation, transition state, and retirement plan |

> **Decision:** Select the thinnest composition that satisfies measured workload requirements and preserves accountable ownership.
>
> **Assumptions:** Requirements, owners, provider obligations, lifecycle burdens, and exit evidence are explicit.
>
> **Trade-off:** Thinner managed composition can reduce internal operation and increase provider dependency; thicker self-hosted or custom composition can increase control and transfer more lifecycle obligations inward.

## Senior, Staff, and Principal decision scope

The role model below is **Handbook synthesis (bounded)**. Titles vary across employers. The distinction here is decision horizon, cross-team reach, organizational constraints, reversibility, and platform evolution, not unsupported team size, request volume, budget, or title prestige. It builds on platform-as-product and shared-workload guidance without claiming that either source defines career levels. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)

### Senior scope

A Senior architect or engineer owns a consequential workload or platform capability end to end. The decision horizon covers implementation, release, operation, and the next material change. Expected artifacts include an interface contract, dependency map, evaluation and release gates, service objectives, telemetry, security review inputs, cost assumptions, runbook, rollback proof, and ADR.

**Illustrative scenario:** A Senior engineer designs the replenishment workload's promotion gate. They ensure that data, model, compatibility, and policy evidence resolve to immutable identities; define alert and rollback behavior; and test the operator path. This is a bounded role example, not a staffing prescription.

The trade-off is local delivery speed against reusable design. The failure mode is a component that functions in isolation but has no support boundary, production evidence, or recovery path. Security and governance reviewers should be brought into the decision rather than represented by a checkbox. Cost analysis covers the capability's build and operational burden. A Senior decision should name which cross-team issue requires Staff escalation.

### Staff scope

A Staff architect owns a cross-team journey or capability portfolio. The horizon includes adoption, common contracts, exception policy, provider selection, migrations, deprecation, shared operations, and the effect of a local choice on several workloads. Evidence includes representative requirements from consuming teams, a responsibility map, reliability and cost boundaries, provider exit analysis, adoption and support signals, and transition states.

**Illustrative scenario:** A Staff architect turns several workload-specific promotion scripts into a supported evidence contract while preserving workload-specific acceptance policies. The platform standardizes identity, policy hooks, deployment records, and rollback evidence; product teams keep product thresholds and risk context.

The trade-off is consistency against specialized needs. Failure modes include standardizing the first team's preference, moving cognitive load into hidden exceptions, or promising a platform contract that capability providers do not meet. Security and governance require a common enforcement boundary plus explicit exception authority. Cost analysis includes migration, support, and deprecation rather than only implementation. A Staff decision should identify enterprise constraints that require Principal resolution.

### Principal scope

A Principal architect owns enterprise boundaries and multi-year evolution. The horizon includes investment allocation, operating model, systemic and correlated risk, vendor concentration, governance interfaces, capability succession, portfolio migration, and retirement. Evidence includes strategic constraints, scenario analysis, portfolio dependencies, funding and capability models, transition architecture, and a review cadence.

**Illustrative scenario:** A Principal architect decides whether model promotion authority remains distributed across business units or converges on a federated control contract. The decision accounts for jurisdiction, product criticality, provider concentration, organizational autonomy, incident command, and migration sequencing without forcing one implementation everywhere.

The trade-off is enterprise coherence against local autonomy and transition cost. Failure modes include optimizing one layer while creating lock-in, fragmented accountability, or an unfunded operating obligation. Security and governance decisions preserve independent authority and escalation. Cost analysis includes stranded capability, parallel operation during migration, and long-term exit. A Principal decision should define what remains locally reversible and which boundary is enterprise-wide.

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
6. **Promotion and reconciliation.** An approved immutable artifact and configuration become desired deployment state. The serving plane reconciles toward that state and reports observed status.
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

**Illustrative scenario:** The entire case is fictional and bounded to the replenishment-ranking workload. It is not a reported company incident, benchmark, or claim about failure frequency. [Figure `fig-04-failure-propagation`: Semantic data change failure](../diagrams/chapter-01/fig-04-failure-propagation.mmd) traces the path.

**Initial architecture:** An upstream inventory service emits a numeric `inventory_age` field. A shared feature component reads it for training and serving. A candidate pipeline validates the schema, evaluates the model, registers an artifact, and promotes through a mutable convenience alias. The serving endpoint reports availability and latency. Product outcomes arrive later.

**Trigger:** The upstream producer changes the field's unit while keeping the name and numeric type. The producer's deployment succeeds, and structural schema validation remains green.

**Propagation:** The online feature path interprets new events under the old semantic contract. The training dataset gradually mixes interpretations. The serving model produces shifted rankings. Exposure changes which products generate future observations, adding direct feedback to the next training data. Direct and hidden feedback are recognized ML system risks. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015)

**Detection:** Endpoint health remains green. A feature-distribution signal changes, but its alert lacks a named response owner. Slice-level product evidence is delayed. A training-serving comparison eventually shows disagreement because the offline replay resolves a different data window. This exposes why unit and end-to-end tests do not establish continuing fitness and why production monitoring must cover system and context change. [`SCULLEY-TECHDEBT-2015`](../sources/references.md#sculley-techdebt-2015) NIST calls for pre-deployment and in-operation testing, production monitoring, and documented response and recovery. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Containment:** The incident owner freezes promotion and CT-triggered candidate admission. The product owner switches the workload to its pre-approved fallback. The platform team blocks the incompatible producer version at the data contract boundary and preserves the active deployment, input samples permitted by policy, logs, decisions, and alias resolution. The risk owner decides whether the workload can continue under the fallback. If risk is unacceptable, operation stops safely until it can be managed, consistent with AI RMF guidance. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Recovery:** The data producer publishes a versioned semantic contract. The feature component implements explicit unit handling. Operators rebuild a clean data reference, replay validation, retrain a candidate, compare it against the last acceptable artifact, and test serving compatibility. The approver reviews the new evidence. Promotion resolves the artifact digest and deployment revision rather than relying on the alias alone. Monitoring labels the restored deployment and watches both immediate service signals and delayed product evidence.

**Prevention:**

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

**Security and governance implications:** The incident could also be caused by unauthorized change, compromised dependencies, or provider behavior. Integrity and access controls must therefore protect source, build, data, artifact, and control records. **Handbook synthesis (bounded):** SLSA Build provenance can provide integrity evidence for qualifying packaged artifacts within its Build-track scope, but it does not establish data semantics, model validity, or deployment approval. This combined control boundary joins SLSA artifact provenance to NIST's separate AI-risk decision semantics; neither source prescribes a complete ML supply-chain decision system. [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) NIST treats multiple trustworthiness characteristics as interacting; restoring availability alone does not close safety, privacy, fairness, or accountability questions. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

**Operational close:** Close the incident only after runtime state, records, alerts, runbooks, product evidence plan, and prevention owners agree. Safe deactivation and decommissioning are part of the lifecycle, not exceptional cleanup. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)

## Architecture decision record exercise

An architecture decision record (ADR) captures a decision, its context and assumptions, considered options, accepted trade-offs, evidence, owner, and review triggers. That definition is handbook synthesis; it is not attributed to an external standard.

**Exercise context - illustrative and bounded:** An organization has three predictive-ML product teams. They need a shared model-evidence and promotion capability across two deployment environments. These quantities exist only for the exercise and are not production evidence. One workload uses sensitive customer data; another has delayed outcome labels; the third runs batch inference. The organization already operates Kubernetes and source control but has limited capacity for another on-call service. It can select a managed registry and pipeline service, self-host third-party software, build a thin control layer over existing capabilities, or create a custom platform.

**Illustrative constraints and targets:** These values are invented solely to make the exercise testable: migration must complete within two quarters; evidence must remain queryable for twelve months; a deployment decision must resolve an immutable artifact and prior rollback target; recovery from control-plane unavailability must be possible within one hour; data and model artifacts must remain in approved regions; and provider exit must preserve records and replay instructions.

**Decision prompt:** Write an ADR that selects a composition for tracking, artifact storage, model registration, approval, promotion, and deployment reconciliation. Do not select a tool solely from a feature list. Show which system is authoritative for each record class, who operates each capability, and how a candidate moves from run to approved deployment.

The ADR must include:

1. **Decision and owner:** one sentence naming the selected composition and accountable decision owner.
2. **Context:** workloads, users, present capabilities, triggering problem, and why the decision is needed now.
3. **Hard constraints:** data, security, governance, reliability, integration, staffing, cost envelope, and exit requirements.
4. **Assumptions:** change rate, workload growth, provider behavior, organizational capacity, and evidence freshness.
5. **Options:** external SaaS, managed cloud, self-hosted third-party, custom, and at least one hybrid composition.
6. **Evidence:** representative prototype, failure injection, restore or redeploy result, identity and data-path review, lifecycle cost model, and provider export test.
7. **Authority map:** canonical source, run, artifact, registry, approval, deployment, incident, and retirement records.
8. **Responsibility map:** platform, product, risk, security, provider, and incident-command handshakes.
9. **Consequences:** benefits, new failure domains, operations, security, governance, cost, and migration work.
10. **Rejected options:** precise rejection reasons tied to constraints rather than preference.
11. **Exit and recovery:** artifact and metadata export, fallback, restore, replacement interface, and decommissioning.
12. **Review triggers:** provider change, cost assumption change, new jurisdiction, new workload type, failed recovery test, control exception, or capability retirement.

**Observable scoring:** A strong answer keeps tracking, artifacts, approval, and deployment state distinct; resolves mutable references to immutable identities; preserves workload accountability; compares lifecycle burden; tests exit; and explains failure handling. A weak answer names a product, calls it the system of record for everything, assumes managed service removes internal responsibility, or omits rollback and retirement.

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

Use the following observable rubric for each answer:

| Score | Observable signals |
| --- | --- |
| 1 - Component answer | Names tools or components without system boundary, assumptions, authority, owner, or recovery; treats a successful job or healthy endpoint as sufficient evidence |
| 2 - Local design | Identifies main flow and some tests, but leaves mutable identities, provider obligations, security, cost, or failure response implicit |
| 3 - Operable architecture | States assumptions; separates control, data, artifact, and telemetry flows; names records and owners; covers trade-offs, security, cost, detection, rollback, and runbooks |
| 4 - Cross-team architecture | Adds reusable contracts, exception and deprecation paths, shared-responsibility handshakes, migration, provider exit, and evidence from representative workloads |
| 5 - Enterprise evolution | Frames decision horizon, portfolio dependencies, correlated risk, investment and operating model, transition states, jurisdiction or governance constraints, and review triggers while preserving local reversibility where appropriate |

**Level calibration:** A Senior candidate should consistently reach score 3 for a workload and explain escalation. A Staff candidate should reach score 4 across multiple teams without erasing workload context. A Principal candidate should reach score 5 on enterprise evolution and still reason concretely about records, incidents, and recovery. These thresholds are **illustrative and bounded** to this handbook rubric, not an external hiring standard.

**Red flags:** Unqualified claims that one vendor mode is cheaper or safer; a model registry treated as complete governance; automation equated with maturity; product outcome delegated entirely to the platform; rollback without data compatibility; security reduced to access control; or a strategic plan without transition and retirement.

## Key takeaways

- The unit of production ML architecture is the system and its decision boundaries, not the model file.
- **Handbook synthesis (bounded):** The lifecycle is a controlled feedback loop. Training produces a candidate; a workload-specific policy authorizes promotion; runtime evidence informs review, recovery, retraining, and retirement. Neither cited source alone prescribes the combined approval architecture. [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024) [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023)
- The seven planes are control, data, training, serving, observability, security and governance, and platform experience. Their purpose is to expose authority and failure boundaries.
- Capability maturity is the strength of evidence, control, recovery, and operating contracts appropriate to a workload. Automation is one capability, not a universal destination.
- **Handbook synthesis (bounded):** Source, data, run, artifact, model, approval, deployment, risk, incident, and retirement facts need canonical records linked by immutable or versioned identities. The cited sources support traceability outcomes but do not prescribe this schema. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024)
- **Handbook synthesis (bounded):** A platform owns reusable journeys and capability contracts. Product teams retain workload behavior and outcome accountability; governance, security, and providers retain their named obligations. This is a starting responsibility pattern rather than a universal organization chart. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)
- **Handbook synthesis (bounded):** Build, buy, managed, self-hosted, and custom decisions require workload evidence, full lifecycle burden, operating ownership, and credible exit proof. The cited sources provide factors, not a universal selection rule. [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025) [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025) [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026) [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023)
- **Handbook synthesis (bounded):** Senior scope makes one workload or capability operable. Staff scope makes a contract reusable across teams. Principal scope makes enterprise boundaries evolvable across a longer decision horizon. This role model is not a cross-employer career standard. [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023) [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025)
- Failure readiness means tracing trigger, propagation, detection, containment, recovery, and prevention before release.
- **Handbook synthesis (bounded):** Reliability, model acceptance, and AI-risk decisions inform one another but do not substitute for one another; neither cited source prescribes the combined control rule. [`NIST-AIRMF-2023`](../sources/references.md#nist-airmf-2023) [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018)

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
- [`NIST-AIRMFPLAYBOOK-2023`](../sources/references.md#nist-airmfplaybook-2023): CH01-C030.
- [`GOOGLECLOUD-MLOPS-2024`](../sources/references.md#googlecloud-mlops-2024): CH01-C031-C032, CH01-C038, CH01-C043-C044, and the Google Cloud portions of qualified synthesis CH01-C059-C060.
- [`GOOGLE-SRESLO-2018`](../sources/references.md#google-sreslo-2018): CH01-C034-C036 and the reliability portion of qualified synthesis CH01-C058.
- [`SLSA-BUILD-2026`](../sources/references.md#slsa-build-2026): CH01-C039-C041 and qualified synthesis CH01-C061.
- [`AWS-MLDESIGN-2025`](../sources/references.md#aws-mldesign-2025): CH01-C045.
- [`AWS-BUILDBUY-2025`](../sources/references.md#aws-buildbuy-2025): CH01-C053 and qualified synthesis CH01-C063.
- [`AWS-MANAGEDSERVICES-2025`](../sources/references.md#aws-managedservices-2025): CH01-C054 and qualified synthesis CH01-C063.
- [`CNCF-PLATFORMS-2023`](../sources/references.md#cncf-platforms-2023): CH01-C046-C047, CH01-C055, and qualified syntheses CH01-C062-C064.
- [`TEAMTOPOLOGIES-TVP-2019`](../sources/references.md#teamtopologies-tvp-2019): CH01-C048.
- [`MICROSOFT-AIWORKLOADS-2026`](../sources/references.md#microsoft-aiworkloads-2026): CH01-C052 and qualified synthesis CH01-C063.
- [`MICROSOFT-WORKLOADS-2025`](../sources/references.md#microsoft-workloads-2025): CH01-C049-C051 and qualified syntheses CH01-C062 and CH01-C064.
- [`NIST-AIRMFSTATUS-2026`](../sources/references.md#nist-airmfstatus-2026): CH01-C065.

The chapter does not rely on bibliography entries that are absent from the coverage map. Applicability limits, source dates, versions, and review deadlines remain authoritative in the claim ledger and bibliography.

## Changelog

**2026-08-23**

- Created the complete Chapter 1 prose with the canonical section sequence.
- Added the seven-plane architecture model, capability maturity model, system-of-record classes, responsibility contract, sourcing framework, role-scope model, lifecycle flow, bounded failure case, ADR exercise, interview questions, and observable rubric.
- Mapped external factual claims to the verified Chapter 1 evidence set and labeled cross-source architectural judgments as bounded handbook synthesis.
- Addressed Task 6 review findings I1, I2, and M1 by labeling repeated qualified syntheses at point of use, reconciling appendix mappings to exact ledger source keys, and adding the role-scope forward boundary.
