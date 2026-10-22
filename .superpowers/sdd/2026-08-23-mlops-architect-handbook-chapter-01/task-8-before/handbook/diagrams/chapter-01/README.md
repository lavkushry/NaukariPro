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

### ML lifecycle and operational feedback loops

- **Figure ID:** `fig-01-ml-lifecycle`
- **Filename:** [fig-01-ml-lifecycle.mmd](fig-01-ml-lifecycle.mmd)
- **Caption:** Figure 1. ML lifecycle and operational feedback loops from product event through retirement.
- **Purpose:** Separate data movement, candidate and deployment evidence, release decisions, and operational feedback while showing that training creates a candidate and does not authorize production use.
- **Assumptions:** The bounded predictive-ML workload has product, platform, release, and risk owners; it can resolve versioned data and immutable deployment identities; batch or human-reviewed variants may replace the online serving path.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata flow; circle-ended arrow = telemetry or feedback flow. Blue nodes are product-team responsibilities, green nodes are platform capabilities, and amber nodes are release or risk authority.
- **Provenance:** Original handbook synthesis
- **Text alternative:** From left to right, a product event enters the platform boundary as captured data and a validated data reference. The reference flows as metadata into a training run, which emits an evaluated candidate for a separate approval decision. Approval produces an immutable deployment reference consumed by the serving workload, which returns a prediction or action to the product boundary. Serving telemetry and product outcomes flow to product review. Review can request retraining, select a prior immutable rollback reference, or create a retirement decision. A feedback edge from the prediction or action to captured data marks model-influenced future observations. Product-team, platform-capability, and release-and-risk-authority subgraphs make responsibility handoffs explicit.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technical Review

### Seven architecture planes

- **Figure ID:** `fig-02-architecture-planes`
- **Filename:** [fig-02-architecture-planes.mmd](fig-02-architecture-planes.mmd)
- **Caption:** Figure 2. Seven architecture planes and their directional contracts.
- **Purpose:** Show the seven planes as authority and responsibility boundaries rather than physical clusters, products, or teams.
- **Assumptions:** One implementation may serve several planes and one plane may span several services; the control-plane pattern is a bounded handbook synthesis rather than a claim that Kubernetes owns enterprise ML lineage or risk decisions.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata flow; circle-ended arrow = telemetry or feedback flow. Purple marks platform experience, amber marks control and security or governance, blue marks execution planes, and green marks observability.
- **Provenance:** Original handbook synthesis
- **Text alternative:** The platform experience plane sends declared requests to the control plane. The security and governance plane supplies policy decisions to control, data, training, and serving. Data moves into training and serving, while serving returns predictions or outcomes through the data plane. Control directs training; training returns candidate artifacts and evaluation metadata to control; control sends an approved immutable deployment reference to serving. Data, training, and serving send telemetry to observability. Observability feeds status back to control and evidence to security and governance; control returns status to the platform experience plane. Each of the seven named nodes is a responsibility boundary, not a required deployment boundary.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technical Review

### Linked systems of record

- **Figure ID:** `fig-03-systems-of-record`
- **Filename:** [fig-03-systems-of-record.mmd](fig-03-systems-of-record.mmd)
- **Caption:** Figure 3. Linked canonical record classes and non-authoritative derived views.
- **Purpose:** Distinguish canonical fact classes, immutable or versioned identity links, decision authority, operational state, and derived catalogs or dashboards.
- **Assumptions:** Products may expose several record classes in one interface, but authority is assigned per fact class; a mutable alias is resolved to an immutable version at decision time; retention and access policy are workload-specific.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata link; circle-ended arrow = telemetry or feedback flow. Blue nodes belong to engineering record authority, amber nodes are canonical decision records, green nodes belong to operations record authority, purple nodes are named decision authorities, orange is the deployment controller, and the gray dashed node is a derived view.
- **Provenance:** Original handbook synthesis
- **Text alternative:** Data producers send workload data into the canonical data and feature record. Within the engineering-record boundary, source and configuration plus data and feature identities link to a run record; the run links to immutable artifact and model-version records. Model and risk evidence flows to the named release authority, which emits a canonical approval record. The approval record flows to the deployment controller, and only that controller issues control flow to deployment and runtime state. Runtime telemetry updates observed deployment state and emits an incident signal to the incident command authority. That authority emits a canonical incident record, which the deployment controller consumes for containment or rollback. Incident and risk records flow to the retirement authority; it emits a canonical retirement record that the deployment controller consumes for deactivation. Records provide evidence to authorities and controllers but do not themselves issue runtime control. Every canonical record class publishes metadata to catalogs and dashboards, which are explicitly labeled derived and non-authoritative.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technical Review

### Semantic data change failure

- **Figure ID:** `fig-04-failure-propagation`
- **Filename:** [fig-04-failure-propagation.mmd](fig-04-failure-propagation.mmd)
- **Caption:** Figure 4. Semantic data change propagation, detection, containment, and recovery.
- **Purpose:** Trace the fictional replenishment-ranking failure from trigger through feedback contamination, incomplete detection, accountable containment, evidence-based recovery, and prevention.
- **Assumptions:** The upstream change preserves field name and numeric type; structural schema checks miss the unit change; outcome labels are delayed; a pre-approved product fallback and prior deployment identity exist; the scenario is not a reported company incident.
- **Legend:** Solid arrow = data flow; dotted arrow = control or decision flow; thick arrow = artifact or metadata flow; circle-ended arrow = telemetry or feedback flow. Purple nodes belong to the data producer, blue nodes to the platform, green nodes to the product team, and amber nodes to incident, release, or risk authority.
- **Provenance:** Original handbook synthesis
- **Text alternative:** In the data-producer boundary, the `inventory_age` unit changes without a name or type change and produces structurally valid events. Data flows into a platform feature component that applies the old meaning, shifting served rankings. Product observations become model-influenced feedback and contaminate the training dataset and a future candidate. Detection is incomplete: schema validation and endpoint availability remain green, the ownerless feature-distribution alert ends on a blind path without triage action, and delayed product evidence is unavailable at detection. A later training-serving comparison reaches incident triage. The incident owner freezes promotion and continuous-training candidate admission, the product owner switches to a pre-approved fallback, the platform independently blocks the incompatible producer version, and the risk owner decides whether fallback operation can continue or must stop safely. In a separate producer-remediation path, triage hands corrective work to the data producer owner, who publishes a versioned semantic contract. That contract flows as metadata to explicit platform unit handling and a clean data reference, followed by retraining, evaluation, compatibility testing, approver review, and an immutable restored deployment. Triage directs prevention controls through control flow; the prevention node names semantic contracts, alert ownership, immutable evidence links, fallback, and rollback tests.
- **Semantic reviewer:** MLOps architecture technical reviewer
- **Review status:** Technical Review

## Review rules

- Keep figure IDs stable once chapter prose cites them.
- Keep component names consistent with the chapter and glossary.
- Record source-key attribution for adapted diagrams.
- Keep reliability evidence, product acceptance evidence, and AI-risk decisions linked but non-substitutable.
- Keep derived catalogs and dashboards visibly outside canonical record authority.
- Advance a figure beyond `Technical Review` only after an independent reviewer verifies its semantics.

## Changelog

### 2026-08-23

- Expanded the diagram scaffold into the binding metadata contract and registered four planned Chapter 1 figures.
- Created and registered four self-contained Mermaid figures with explicit flow legends, text alternatives, responsibility boundaries, and `Technical Review` status.
- Corrected Figure 3 authority-to-record-to-controller directionality and Figure 4 containment, producer-remediation, blind-alert, prevention, and solid-edge semantics after technical review finding I4.
