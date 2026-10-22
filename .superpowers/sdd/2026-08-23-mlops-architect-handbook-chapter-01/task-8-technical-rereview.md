# Task 8 Independent Technical Architecture Rereview

## Verdict

**REQUEST CHANGES — not technically approved.** Counts: **Critical 0 | Important 2 | Minor 0**. The corrections close the original defects at their named locations, but two cross-file architecture inconsistencies remain. Chapter 1 and all four diagrams must remain in `Technical Review` until an independent scoped rereview finds zero Critical and zero Important findings.

## Scope and verification

This rereview read the prior technical review, the current complete Chapter 1, all four Mermaid sources, the complete diagram registry and text alternatives, claim-ledger rows `CH01-C066` through `CH01-C072`, the evidence, technical, and editorial fix reports, and the complete Task 8 review-package diff. The latest editorial rewrites were included in the semantic review.

The live checks produced these results:

- `bash mlops/architect-handbook/scripts/test_validate_handbook.sh`: exit 0; all 27 tests passed.
- `bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook`: exit 0; all 11 structure checks passed.
- `bash mlops/architect-handbook/scripts/validate_handbook.sh --profile release mlops/architect-handbook`: exit 0; all 12 release checks passed.
- Static Mermaid audit: 4/4 files declare `flowchart`; all subgraph/end pairs are balanced; all edge endpoints are defined; all four registered edge forms occur in every figure; no external URL, image, click, or initialization directive occurs.
- Chapter-registry audit: 4/4 point-of-use diagram links and 4/4 text-alternative links resolve to registered figures; every figure has all ten required registry fields.
- Ledger audit: `CH01-C066` through `CH01-C069` are `verified`; `CH01-C070` through `CH01-C072` are explicitly `qualified`.
- `mmdc` is unavailable, so this rereview makes no rendered-layout claim.

Automated validation is necessary but does not exercise the semantic authority and ownership conflicts below.

Apart from R1 and R2, the rereview found no new data, artifact, or telemetry-direction regression; recovery regression; CI/CD-versus-CT regression; provider-boundary regression; governance, reliability, security, cost, or operations regression; build/buy/managed-service regression; or Senior/Staff/Principal calibration regression.

## Exact reconciliation of prior findings

| Prior finding | Rereview result | Exact evidence |
| --- | --- | --- |
| I1 | Closed at the corrected Figure 3 boundary. A separate Figure 1 regression is reported as R1. | `fig-03-systems-of-record.mmd:48`, `:55-60`, and `:72`; Chapter 1 `:238-240` |
| I2 | Closed. Producer bytes terminate at the workload-data store; only identity, boundary, and contract metadata link to the data-and-feature record. | `fig-03-systems-of-record.mmd:36-37`; registry `:58` and `:61`; Chapter 1 `:238` |
| I3 | Closed. Candidate bytes go to the artifact authority/store; control receives references only; serving resolves the immutable artifact independently. | `fig-02-architecture-planes.mmd:22-25`; registry `:44-48`; Chapter 1 `:106` |
| I4 | The original product-review bypass is closed. The new direct authority-to-runtime path in the same figure is reported as R1. | `fig-01-ml-lifecycle.mmd:33-38`; registry `:35`; Chapter 1 `:74` |
| I5 | Closed. Producer and candidate quarantine, fallback, safe stop, and independent availability telemetry now have visible effect paths. | `fig-04-failure-propagation.mmd:67-77`, `:82-83`, and `:101-109`; Chapter 1 `:495-499` |
| I6 | Closed. Recovery bounds affected data, separates provable normalization from indeterminate data, and proceeds through approval, desired state, reconciliation, and observed restoration. | `fig-04-failure-propagation.mmd:78-99`; registry `:74`; Chapter 1 `:501-505` |
| I7 | Closed as originally scoped: CI/CD, CT, and model release are named independently, and successful CT or software build does not authorize production. R1 identifies a remaining writer/actuator ambiguity across the complete architecture. | Chapter 1 `:214-220` |
| I8 | Closed. The contract now names bounded provider duties while retaining internal platform, workload, risk, and incident authority. | Chapter 1 `:300-342` and `:344-346`; ledger `CH01-C072` |
| M1 | Closed. Signing is paired with trusted provenance and digest verification plus policy admission, and signing alone is explicitly bounded. | Chapter 1 `:136`; ledger `CH01-C069` and `CH01-C071` |

## Findings

### Critical

None.

### Important

#### R1. Figure 1 bypasses the passive desired-state record and deployment controller

**Evidence:** Figure 1 sends a dotted control edge directly from `ReleaseRiskDecision` to `ServingWorkload` at `mlops/architect-handbook/diagrams/chapter-01/fig-01-ml-lifecycle.mmd:39`. Its approved and rollback references also terminate directly at that workload at `:45-46`. The registered text alternative preserves the same model by saying the release and risk authority “directs serving deactivation or rollback” at `mlops/architect-handbook/diagrams/chapter-01/README.md:35`.

That direction conflicts with the corrected canonical contract. Chapter 1 says an authorized workflow writes the passive desired-state record and the deployment controller watches and actuates the workload at `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:240` and `:464`. Figure 3 implements that contract at `mlops/architect-handbook/diagrams/chapter-01/fig-03-systems-of-record.mmd:48`, `:55-60`, and its text alternative says the controller issues the only runtime-control edge at `mlops/architect-handbook/diagrams/chapter-01/README.md:61`. Stage 3 additionally leaves the writer boundary indeterminate by saying the model-release controller “writes or reads” the desired reference at `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:218`.

**Impact:** The chapter presents two incompatible actuation contracts. One permits release/risk authority and references to target serving directly; the other permits only the deployment controller to act after desired state is recorded. This recreates the authority confusion the Chapter 1 control plane is intended to prevent and leaves rollback, deactivation, and normal promotion with no single auditable writer/controller boundary.

**Concrete fix:** In Figure 1, replace direct authority/reference-to-workload edges with `authorized decision -> passive desired deployment record -> deployment controller -.-> serving workload`; route approved and rollback immutable identities into the desired record, and route retirement into deactivation desired state. Preserve workload telemetry as observed state. Update the text alternative to distinguish authority decision, authorized desired-state write, controller actuation, and observed status. In Stage 3, replace “writes or reads” with an unequivocal contract: the authorized release workflow writes the desired reference; the deployment controller watches it and alone actuates runtime. If one implementation performs both roles, state that its separately gated identities and permissions still preserve those two logical authorities.

#### R2. Figure 4 assigns workload and model-behavior accountability to the platform

**Evidence:** Figure 4 labels its blue boundary `Platform responsibility` at `mlops/architect-handbook/diagrams/chapter-01/fig-04-failure-propagation.mmd:10`, then places `ShiftedRankings`, `MixedTrainingData`, and `FutureCandidate` inside that boundary at `:15-17`; the class assignment at `:123` reinforces that ownership. The registry makes the color semantic explicit: “blue nodes [belong] to the platform” at `mlops/architect-handbook/diagrams/chapter-01/README.md:72`.

The prose establishes a different responsibility contract. Product owns workload intent, acceptance criteria, model behavior, and outcome review at `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:74`; owns feature logic, training intent, acceptance criteria, and product behavior at `:307-310`; and owns model behavior and outcome measurement at `:332-336`. Platform owns hooks, reusable orchestration, artifact interfaces, deployment mechanisms, dependency restoration, and guardrails at `:308`, `:313`, `:318`, and `:323`. Figure 1 correctly calls its comparable boundary “Platform execution mechanisms — not owner of workload behavior or outcomes” at `mlops/architect-handbook/diagrams/chapter-01/fig-01-ml-lifecycle.mmd:10`.

**Impact:** During the failure case, the ownership legend routes semantic feature contamination, model behavior, and candidate acceptability to the platform even though the chapter assigns those decisions to the workload team. A reader cannot use the diagram to determine who owns remediation and acceptance versus who operates admission, training, serving, and deployment mechanisms.

**Concrete fix:** Make Figure 4 use the same accountability/mechanism split as Figure 1. Keep the admission gate, reusable feature/training/serving mechanisms, quarantine mechanism, and deployment controller under platform execution responsibility. Put workload-specific feature semantics, training intent, candidate acceptability, shifted model behavior, fallback behavior, and outcome review under product/workload accountability, while retaining producer contract ownership and independent incident/release/risk decisions. If mixed-data and shifted-ranking nodes are intended only as observed states rather than owned responsibilities, rename the subgraph and registry legend accordingly and add explicit owner/action nodes so containment is not inferred from color or containment.

### Minor

None.

## Approval gate

**Technical approval is denied.** Counts: **Critical 0 | Important 2 | Minor 0**. Correct R1 and R2, update the affected prose and text alternatives, rerun the static and validator checks, and perform a scoped semantic rereview. A validator pass alone is not sufficient.

## Changelog

### 2026-08-23

- Completed the focused Task 8 technical rereview after evidence, technical, and editorial corrections.
- Verified the exact disposition of I1-I8 and M1, all four Mermaid sources and registered text alternatives, ledger rows C066-C072, 27 tests, and both validation profiles.
- Recorded two Important cross-file authority and ownership findings; technical approval remains denied.
