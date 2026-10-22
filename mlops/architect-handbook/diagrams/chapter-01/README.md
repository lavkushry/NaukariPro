# Chapter 1 Diagrams

## Purpose

This directory is the figure registry for the editable, text-based diagrams that support Chapter 1. Each Mermaid source includes an explicit legend and names the responsibility boundaries reviewed against the chapter prose.

## Metadata contract

Each registry entry provides these fields:

- Figure ID
- Filename
- Caption
- Purpose
- Assumptions
- Legend
- Provenance
- Text alternative
- Semantic reviewer
- Review status

Use `Original handbook synthesis` for a new diagram. An adapted diagram names its source key and describes the adaptation. The semantic reviewer verifies arrow direction, responsibility boundaries, labels, and the relationship between the diagram and the associated chapter prose.

## Figure registry

### Figure fig-01-ml-lifecycle

- **Figure ID:** `fig-01-ml-lifecycle`
- **Filename:** [fig-01-ml-lifecycle.mmd](fig-01-ml-lifecycle.mmd)
- **Caption:** Figure 1. ML lifecycle and operational feedback loops from product event through retirement.
- **Purpose:** Separate product requests, platform execution mechanisms, release and risk decisions, passive desired deployment state, controller actuation, and observed state while showing that training creates a candidate and does not authorize production use.
- **Assumptions:** The bounded predictive-ML workload has product, platform, release, and risk owners; the product team owns workload behavior, acceptance criteria, serving objectives, and outcomes; platform capabilities execute authorized work; versioned data and immutable deployment identities are resolvable; if one product implements the release workflow and deployment controller, separately gated identities and permissions preserve their logical authorities; batch or human-reviewed variants may replace the online serving path.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata flow; circle-ended arrow = telemetry or feedback flow. Blue nodes are product-team responsibilities, green nodes are platform capabilities, and amber nodes are release or risk authority.
- **Provenance:** Original handbook synthesis
- **Text alternative:** Product workload intent and acceptance criteria enter a declared-intent record while a product event enters the platform data-capture mechanism and validated data reference. A product review request can submit retrain, rollback, or retirement intent only through declared intent. Release and risk authority decides which action is permitted. The training mechanism creates an evaluated candidate for a separate approval decision. Approval resolves an approved immutable deployment reference; authorized rollback resolves a prior immutable reference; retirement resolves deactivation state. The authorized release workflow writes its selected reference or deactivation state to a passive desired deployment record. A deployment controller watches that record, alone actuates runtime through the serving mechanism, and records reconciliation status. No authority or reference directly actuates serving. Workload telemetry contributes observed runtime facts, and the combined observed deployment state returns to product review. The serving mechanism returns a prediction or action, while a feedback edge to captured data marks model-influenced observations. Product owns workload behavior and outcomes; platform supplies execution mechanisms without absorbing that accountability.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technically approved

### Figure fig-02-architecture-planes

- **Figure ID:** `fig-02-architecture-planes`
- **Filename:** [fig-02-architecture-planes.mmd](fig-02-architecture-planes.mmd)
- **Caption:** Figure 2. Seven architecture planes and their directional contracts.
- **Purpose:** Show the seven planes as authority and responsibility boundaries rather than physical clusters, products, or teams, while separating immutable artifact storage from control-plane decisions.
- **Assumptions:** One implementation may serve several planes and one plane may span several services; the artifact authority or store is a linked record capability rather than an eighth architecture plane; the control-plane pattern is a bounded handbook synthesis rather than a claim that Kubernetes owns enterprise ML lineage or risk decisions.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata flow; circle-ended arrow = telemetry or feedback flow. Purple marks platform experience, amber marks control and security or governance, blue marks execution planes, and green marks observability.
- **Provenance:** Original handbook synthesis
- **Text alternative:** The platform experience plane sends declared requests to the control plane. The security and governance plane supplies policy decisions to control, data, training, and serving. Data moves into training and serving, while serving returns predictions or outcomes through the data plane. Control directs training. Training writes candidate artifact bytes to the artifact authority and store, and sends only candidate identity and evaluation-evidence references to control. Control owns the decision and approved immutable desired reference; it does not broker artifact bytes. A model-release controller applies that decision, while serving resolves the corresponding immutable artifact from the artifact authority. Data, training, and serving send telemetry to observability. Observability feeds status back to control and evidence to security and governance; control returns status to the platform experience plane. Each of the seven plane nodes is a responsibility boundary, not a required deployment boundary; the linked artifact store is not an additional plane.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technically approved

### Figure fig-03-systems-of-record

- **Figure ID:** `fig-03-systems-of-record`
- **Filename:** [fig-03-systems-of-record.mmd](fig-03-systems-of-record.mmd)
- **Caption:** Figure 3. Linked canonical record classes and non-authoritative derived views.
- **Purpose:** Distinguish canonical fact classes, immutable or versioned identity links, decision authority, operational state, and derived catalogs or dashboards.
- **Assumptions:** Products may expose several record classes in one interface, but authority is assigned per fact class; workload-data bytes are stored separately from the data-and-feature metadata authority; a mutable alias is resolved to an immutable version at decision time; retention and access policy are workload-specific.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata link; circle-ended arrow = telemetry or feedback flow. Blue nodes belong to engineering record authority, amber nodes are canonical decision records, green nodes belong to operations record authority, purple nodes are named decision authorities, orange is the deployment controller, and the gray dashed node is a derived view.
- **Provenance:** Original handbook synthesis
- **Text alternative:** Data producers send solid workload-data flow to a dataset and workload-data store. Only the store's immutable or versioned identity, event boundary, pointer, and contract metadata link to the canonical data and feature record. Within the engineering-record boundary, source and configuration plus data and feature identities link to a run record; the run links to immutable artifact and model-version records. Model and risk evidence flows to the named release authority, which emits a canonical approval record. Approved, incident, rollback, or retirement decisions are resolved into desired state in the passive deployment and runtime record. The deployment controller watches that desired state, issues the only runtime control edge to the runtime workload, and records reconciliation status. Workload telemetry independently updates observed state; the deployment record can then emit an incident signal. Incident and retirement authorities create their decision records, but those records only update desired facts and do not actuate the workload. Every canonical record class publishes metadata to catalogs and dashboards, which are derived and non-authoritative.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technically approved

### Figure fig-04-failure-propagation

- **Figure ID:** `fig-04-failure-propagation`
- **Filename:** [fig-04-failure-propagation.mmd](fig-04-failure-propagation.mmd)
- **Caption:** Figure 4. Semantic data change propagation, detection, containment, and recovery.
- **Purpose:** Trace the fictional replenishment-ranking failure while separating producer contract ownership, product workload accountability, platform execution mechanisms, neutral observed facts, and independent incident, release, and risk authority through containment and recovery.
- **Assumptions:** The upstream change preserves field name and numeric type; structural schema checks miss the unit change; outcome labels are delayed; producer revision or event-time provenance can bound at least part of the incident; records whose unit remains indeterminate are not reconstructed; workload feature, training, acceptance, fallback, and outcome owners are named; a pre-approved product fallback and prior deployment identity exist; the scenario is not a reported company incident.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata flow; circle-ended arrow = telemetry or feedback flow. Purple nodes belong to the data producer; blue nodes are platform execution mechanisms and do not own workload behavior or outcomes; green nodes are product workload accountability; amber nodes are independent incident, release, or risk authority; gray dashed nodes are neutral observed state and evidence whose actions come from explicitly named owners.
- **Provenance:** Original handbook synthesis
- **Text alternative:** The producer owns the `inventory_age` change and versioned semantic contract. Structurally valid events enter the platform data-admission mechanism. Product-owned workload feature semantics still express the old unit meaning; the reusable feature and serving mechanisms execute those semantics, producing product-owned shifted model behavior. Model-influenced outcomes mix unit interpretations in product-owned training data. Product training intent invokes the platform training mechanism, which produces a contaminated workload candidate for the named product candidate-acceptance owner. Gray nodes record neutral evidence: schema and availability may remain green, the ownerless feature alert reaches a blind path, delayed outcome evidence reaches the product outcome-review owner only later, and a training-serving mismatch reaches independent incident triage. Containment uses explicit owners and mechanisms: platform quarantine blocks the producer revision at admission and holds the candidate; the product owner records rejection or hold evidence and selects pre-approved fallback behavior; the platform fallback-serving mechanism executes it. The independent risk decision authorizes and resolves continuation-under-fallback or safe-stop state; an authorized incident workflow writes that selected state to the passive desired deployment record. Recovery establishes the producer revision and event-time boundary, normalizes provable units, quarantines or discards an indeterminate interval, and waits for a verified post-fix window when reconstruction is not defensible. The producer publishes the contract, the product feature owner records explicit unit semantics, and the platform feature mechanism executes them. Product training intent invokes clean-data retraining and evaluation; the candidate-acceptance owner supplies evidence to the independent approver. The independent approval decision authorizes and resolves the approved immutable reference; an authorized release workflow writes that selected state to the passive desired deployment record. The deployment controller watches that record and alone actuates runtime through the serving mechanism. Controller status plus workload telemetry establish neutral observed restored state. Triage separately directs prevention controls.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technically approved

## Review rules

- Keep figure IDs stable once chapter prose cites them.
- Keep component names consistent with the chapter and glossary.
- Keep the natural ATX heading derived from each figure ID stable so point-of-use text-alternative links do not move when a caption changes.
- Associate the registered text alternative with the rendered figure in every publication format; color and arrow shape must not be the only carriers of meaning.
- Record source-key attribution for adapted diagrams.
- Keep reliability evidence, product acceptance evidence, and AI-risk decisions linked but non-substitutable.
- Keep derived catalogs and dashboards visibly outside canonical record authority.
- Advance a figure from `Technical Review` to `Technically approved` only after an independent reviewer verifies its semantics and closes all Critical, Important, and Minor findings.
- Before publication readiness, render every source with the approved Mermaid CLI, validate SVG output as XML, and inspect SVG or PNG output for clipping and collisions. Keep verification renders outside the maintained handbook unless a later publication task explicitly adopts them as assets.

## Final render verification

Mermaid CLI `@mermaid-js/mermaid-cli` 11.16.0 rendered all four registered sources to SVG and PNG in `/private/tmp/mlops-handbook-mermaid`. `xmllint` validated all 4 SVG files, and visual inspection of all four PNGs found no clipping or collision. The eight outputs are verification artifacts only and are not added to the handbook.

## Changelog

### 2026-08-23

- Advanced all four figure entries from `Technical Review` to `Technically approved` after the final technical review and FM1 closure reached Critical 0, Important 0, Minor 0.
- Replaced the stale renderer-unavailable caveat with Mermaid CLI 11.16.0 evidence: 4 SVG and 4 PNG renders, 4/4 XML-valid SVGs, and visual inspection with no clipping or collision; kept outputs outside the handbook as verification artifacts.
- Closed Task 8 technical rereview findings R1 and R2 by routing Figure 1 decisions and references through passive desired state and controller-only actuation, and by separating Figure 4 product accountability, platform mechanisms, producer ownership, neutral evidence, and independent authority.
- Added stable natural ATX anchors derived from all four figure IDs and required publication renderers to associate each registered text alternative with its figure.
- Corrected Task 8 technical findings across all four figures: request and authority separation, artifact-byte boundaries, passive desired-state records, controller actuation, workload-data storage, visible containment effects, data-recoverability rules, and reconciled restoration.
- Updated every figure assumption and text alternative to distinguish product accountability, platform mechanisms, provider-neutral record authority, independent telemetry, and the CI/CD, CT, and model-release boundaries described in Chapter 1.
- Expanded the diagram scaffold into the binding metadata contract and registered four planned Chapter 1 figures.
- Created and registered four self-contained Mermaid figures with explicit flow legends, text alternatives, responsibility boundaries, and `Technical Review` status.
- Corrected Figure 3 authority-to-record-to-controller directionality and Figure 4 containment, producer-remediation, blind-alert, prevention, and solid-edge semantics after technical review finding I4.
