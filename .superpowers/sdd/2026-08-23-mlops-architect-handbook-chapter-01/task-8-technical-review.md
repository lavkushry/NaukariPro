# Task 8 Independent Technical Architecture Review

## Verdict

**REQUEST CHANGES — not technically approved.** The review found **0 Critical, 8 Important, and 1 Minor** findings. Chapter 1 and all four diagrams must remain in `Technical Review`. Approval requires correction and scoped technical rereview with zero Critical and zero Important findings.

The local release validator exits 0, but it does not detect the authority, flow-direction, recovery, and ownership defects below.

## Scope and method

The review read in full `AGENTS.md`, `CLAUDE.md`, the approved design, Task 8 brief, Chapter 1, all four Mermaid sources, the diagram registry and text alternatives, glossary, all 65 claim-ledger rows, bibliography, style guide, editorial status, and the Task 6 review/rereview and Task 7 review. The seven planes, record authorities, lifecycle feedback, continuous integration and continuous delivery (CI/CD), continuous training (CT), governance, reliability, sourcing modes, provider boundaries, and Senior/Staff/Principal calibration were checked independently of prior approvals.

The `ecc:agent-architecture-audit` skill was applied only for applicability. Chapter 1 explicitly limits itself to predictive ML and defers generative and agentic extensions (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:5`, `:24`, and `:356`). It defines no agent loop, tool router, memory path, repair pass, or LLM transport layer, so forcing the skill's 12-layer agent model onto this chapter would be incorrect. The explicit deferral is technically sound.

Static Mermaid inspection found four valid `flowchart` declarations, balanced subgraphs, defined edge endpoints, the four documented edge forms, and no external URL, image, click, or initialization directive. `mmdc` is unavailable, so this review makes no render-success claim. Semantic review remains failing for the reasons below.

## Findings

### Critical

None.

### Important

#### I1. Figure 3 directs control at a record but never at the runtime workload

**Evidence:** `mlops/architect-handbook/diagrams/chapter-01/fig-03-systems-of-record.mmd:37` sends controller control flow to `DeploymentRuntime`, whose label says it is a deployment and runtime **record**. `:48`, `:52`, and `:56` feed approval, incident, and retirement records to the controller, but there is no controller-to-`RuntimeWorkload` edge. `:69` only sends telemetry from the workload into the record. The text alternative nevertheless says that only the controller issues control to runtime state (`mlops/architect-handbook/diagrams/chapter-01/README.md:61`). The prose separately says deployment records describe desired and observed state and that the serving plane reconciles toward desired state (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:207-211` and `:341`).

**Impact:** The diagram turns the system of record into the apparent actuation target and leaves deployment, rollback, and deactivation with no path to the actual workload. It does not demonstrate the control-loop contract established at chapter line 93.

**Concrete fix:** Show approval or retirement policy writing desired state to the canonical deployment record; show the controller watching that state; add `DeploymentController -.-> RuntimeWorkload`; retain `RuntimeWorkload --o DeploymentRuntime` for observed state; and show the controller recording reconciliation status. Update the text alternative to distinguish desired-state authority, controller actuation, workload execution, and observed-state recording.

#### I2. Figure 3 makes the data-and-feature record a workload-data sink

**Evidence:** `mlops/architect-handbook/diagrams/chapter-01/fig-03-systems-of-record.mmd:35` uses the solid data-flow edge `DataProducers --> DataFeature`. The registry says producers send workload data into the canonical record (`mlops/architect-handbook/diagrams/chapter-01/README.md:61`). The prose instead defines this record as identities, pointers or event boundaries, contracts, time windows, access decisions, and deletion state, and explicitly distinguishes a pointer from a stored copy (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:189-193`).

**Impact:** The figure collapses the data plane or dataset store into the metadata authority, obscuring storage, access, retention, and deletion ownership. That contradicts the chapter's record-class boundary and can lead readers to treat a catalog entry as the data itself.

**Concrete fix:** Add a workload data-path or dataset-store node receiving the solid data edge, then link its immutable/versioned identity and contract metadata to `DataFeature` with `==>`. If the physical data store is intentionally also authoritative, say so as a bounded assumption and still distinguish bytes from the metadata record in the node and text alternative.

#### I3. Figure 2 implies candidate artifacts transit through the control plane

**Evidence:** `mlops/architect-handbook/diagrams/chapter-01/fig-02-architecture-planes.mmd:21-22` shows `Training ==> Control ==> Serving`. The registry expands that into “training returns candidate artifacts and evaluation metadata to control” and control then sends the deployment reference to serving (`mlops/architect-handbook/diagrams/chapter-01/README.md:48`). The prose assigns artifact bytes to an artifact record/store and assigns the control plane authoritative desired state, policy, reconciliation, and corrective action (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:91-95` and `:195-205`).

**Impact:** The seven-plane figure weakens the control/artifact boundary by making the control plane look like an artifact broker or store. This increases conceptual blast radius and conflicts with the later record-authority model.

**Concrete fix:** Label the training-to-control flow as candidate identity plus evaluation-evidence references, not candidate bytes. Show artifact bytes going to the artifact authority/store and serving resolving the approved immutable reference from that authority. Keep control responsible for the decision and desired reference only. Update Figure 2's text alternative accordingly.

#### I4. Figure 1 lets product review bypass declared intent and blur release/risk authority

**Evidence:** `mlops/architect-handbook/diagrams/chapter-01/fig-01-ml-lifecycle.mmd:31` is the declared-intent path to training, but `:33` adds a second direct product `ReviewDecision -.-> TrainingRun` path. `:34-35` likewise sends product review directly to the rollback reference and retirement record inside the release-and-risk authority subgraph. The registry says review can request retraining, select rollback, or create retirement (`mlops/architect-handbook/diagrams/chapter-01/README.md:35`). The prose says product-risk and technical-release owners define what a trigger may do and that the control plane creates the training request (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:69-75` and `:336-343`).

**Impact:** A product-team decision appears able to initiate controlled execution and create authority records without the policy/authority handshake that the chapter treats as foundational. The same figure places the entire training run and serving workload inside a platform-capability box even though workload behavior and end-to-end objectives remain product-team accountability (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:229-237`).

**Concrete fix:** Rename the product node to a review/request, route it into declared intent, and let the control/release/risk authority issue training, rollback, and retirement decisions. Separate platform execution mechanisms from workload-owned training intent, model behavior, and serving objectives, or annotate the shared ownership explicitly. Make the text alternative use “request” and “authority decides” consistently.

#### I5. Figure 4 issues containment commands but shows no containment effect

**Evidence:** Failure propagation runs uninterrupted through `UnitChange` to `FutureCandidate` at `mlops/architect-handbook/diagrams/chapter-01/fig-04-failure-propagation.mmd:42-47` and `:57`. Triage sends commands to freeze promotion, switch fallback, block the producer, and make a risk decision at `:48-52`, but all four action nodes are dead ends. `FreezePromotion` does not quarantine the future candidate, `BlockProducer` does not gate the incompatible data path, `PreapprovedFallback` does not bypass shifted rankings, and `RiskDecision` reaches neither a continue-under-fallback nor a stop state. The registry promises accountable containment (`mlops/architect-handbook/diagrams/chapter-01/README.md:70`, `:74`), and the prose describes each containment outcome (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:370`).

**Impact:** The failure diagram records that commands were issued but cannot show that exposure, contaminated admission, candidate promotion, or unsafe operation stopped. This is not an adequate failure-propagation or recovery boundary.

**Concrete fix:** Add explicit containment-result nodes and directional edges: producer-version quarantine at the data-admission gate, candidate quarantine/no promotion, fallback serving to the product path, and risk-authorized continuation or safe stop. Connect each action to the propagation edge it interrupts or bypasses. Also replace `ShiftedRankings --o EndpointGreen` at `:66` with independent service telemetry from the serving workload; shifted ranking quality does not cause endpoint availability to remain green.

#### I6. Figure 4's recovery is neither data-recoverable nor deployment-reconciled

**Evidence:** `mlops/architect-handbook/diagrams/chapter-01/fig-04-failure-propagation.mmd:58-61` derives a clean data reference from a newly versioned contract and explicit unit handling but shows no raw-data provenance, affected-time boundary, normalization, or quarantine of already mixed records. `:63-64` then jumps from recovery evidence to approver review and directly to a restored deployment. The prose similarly says operators rebuild a clean data reference and then promote the digest/revision (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:372`), while its prevention rule explicitly requires candidate creation, approval, promotion, and runtime reconciliation to remain separate (`:380`).

**Impact:** A contract published after the incident cannot by itself identify or repair historical records whose unit was not recorded. The direct approval-to-deployment edge also bypasses the promotion authority, desired-state record, controller action, and observed-state verification required elsewhere in the chapter.

**Concrete fix:** State how the affected producer revision or event-time boundary is established and how records are normalized or quarantined. If contaminated rows cannot be distinguished, require discarding that interval or waiting for a verified post-fix window instead of claiming reconstruction. Extend the diagram through candidate artifact, approval record, immutable desired deployment reference, controller reconciliation, and observed restored state before declaring recovery.

#### I7. Stage 3 overloads CI/CD with model-candidate promotion and obscures the CT boundary

**Evidence:** The chapter first says Google's model separates manual delivery, automated ML pipelines, and CI/CD for **pipeline changes** (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:137-139`). Stage 2 creates candidates (`:155-159`). At Stage 3, however, the grammar makes “CI/CD” the actor that validates pipeline changes, resolves immutable artifacts, enforces approval, and deploys progressively (`:161-165`). The lifecycle section correctly says CT may create a candidate while promotion is separate (`:69`), so the Stage 3 wording conflicts with the chapter's own distinction.

**Impact:** Readers can infer that a pipeline-code CI/CD workflow and a model-release workflow are one controller. That invites a CT trigger or successful software build to acquire unintended promotion authority.

**Concrete fix:** Name three independently gated subjects: CI/CD builds, tests, and deploys pipeline/serving code and configuration; CT creates and evaluates a candidate model; a model-release controller consumes an approved immutable model/runtime bundle and reconciles deployment. State whether approval is manual or automated policy and preserve the rule that CT success never authorizes production by itself.

#### I8. The responsibility contract has no explicit provider-owned obligations

**Evidence:** The responsibility table has columns only for platform, product/workload, and shared or independent authority (`mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:229-237`). Its provider row assigns internal platform, product, contract-owner, and coordination duties but no duty to the provider (`:236`). The outage scenario again says internal owners coordinate when a managed provider causes failure (`:241`). The build/buy section lists provider-related evaluation factors and internal burdens (`:261-289`) but never establishes the provider side of the operating handshake.

**Impact:** The chapter correctly says managed service does not remove internal workload risk, but it leaves the other half of shared responsibility implicit. Contracted service operation, incident notice, security response, change communication, data deletion, evidence export, support, and exit duties have no owner in the reference responsibility model.

**Concrete fix:** Add a capability-provider column or a companion provider contract. At minimum name provider obligations for service operation and limits, security/vulnerability response, change and deprecation notice, data location/retention/deletion, telemetry and audit export, incident escalation, recovery support, portability, and termination. Keep platform integration and product outcome accountability internal and explicit.

### Minor

#### M1. Artifact signing is described as reducing attack paths

**Evidence:** `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:107` says isolation, secret scoping, dependency integrity, and artifact signing “reduce attack paths.” Signing does not reduce the available paths by itself; trusted verification and admission policy prevent or detect acceptance of an unauthorized artifact.

**Concrete fix:** Replace the phrase with wording such as: “Isolation and secret scoping reduce exposure; dependency integrity plus signing and verification support detection and rejection of unauthorized artifacts.” Name the verification/admission step wherever signing is relied on.

## Architecture diagnosis and ordered correction plan

The primary failure mode is semantic collapse between **records, decisions, controllers, and executing workloads**. Figure 3 makes this explicit; Figures 1 and 4 repeat it by letting requests or approval edges skip authority and reconciliation. A second failure mode is **responsibility collapse**: platform mechanisms are drawn as owning workload behavior, while provider obligations are absent. The CI/CD sentence then collapses distinct change subjects into one release actor.

Correct in this order:

1. Repair Figure 3's desired-state, controller, runtime, telemetry, and data-record directions; then update its text alternative.
2. Repair Figure 4's containment effects, contaminated-data recovery proof, promotion/reconciliation path, and telemetry causality; then update its text alternative.
3. Repair Figure 1's request-to-authority handshakes and shared platform/product ownership.
4. Narrow Figure 2 artifact movement to immutable references and evidence metadata.
5. Split CI/CD, CT, and model release into separately authorized workflows in prose and diagrams.
6. Add explicit provider obligations and recheck platform/product/provider handshakes across the sourcing table, case study, ADR exercise, and interview rubric.
7. Apply the signing/verification wording correction, rerun static Mermaid and handbook validation, and perform a scoped semantic rereview of every changed prose statement, arrow, legend, and text alternative.

## Approval gate

**Technical approval is denied.** Counts: **Critical 0 | Important 8 | Minor 1**. All eight Important findings require correction and independent scoped rereview. Static syntax and validator success are necessary but are not sufficient for approval.

## Changelog

### 2026-08-23

- Completed the independent Task 8 technical architecture review of Chapter 1, the seven-plane model, lifecycle and record authorities, ownership contracts, failure/recovery flow, CI/CD/CT boundaries, role calibration, and all four diagrams.
- Applied the agent-architecture audit only to its actual scope and recorded that agent/LLM architecture is explicitly deferred.
- Recorded zero Critical, eight Important, and one Minor finding; technical approval remains denied.
