# Glossary

## Controlled terms

The entries below define the Chapter 1 vocabulary. An external source key means the cited source entails the wording within the stated scope. `Handbook synthesis` marks a local architectural definition rather than an externally standardized term. Each entry follows the same linear order: definition, aliases, source key, verification state, then notes.

### Machine learning operations (MLOps)

- **Definition:** An engineering practice that applies automation and monitoring across machine learning system construction; integration; testing; release; deployment; and infrastructure management.
- **Aliases:** ML operations
- **Source key:** `GOOGLECLOUD-MLOPS-2024`
- **Verification state:** Verified
- **Notes:** Google Cloud's definition is scoped primarily to predictive artificial intelligence systems. Expand MLOps at first use in each chapter.

### Machine learning (ML) system

- **Definition:** A production system whose behavior depends on learned models plus data; code; configuration; pipelines; infrastructure; consumers; and feedback.
- **Aliases:** ML system
- **Source key:** `SCULLEY-TECHDEBT-2015`
- **Verification state:** Verified
- **Notes:** The definition follows the paper's system boundary rather than treating the model file as the whole system. Expand ML at first use in each chapter.

### Control plane

- **Definition:** The Kubernetes components that expose the cluster application programming interface; store API data; schedule workloads; and run controller processes.
- **Aliases:** None
- **Source key:** `KUBERNETES-COMPONENTS-2026`
- **Verification state:** Verified
- **Notes:** Rechecked for Kubernetes v1.36 against the readable page and immutable official source revision. This definition is Kubernetes-specific; any enterprise ML extension must be labeled handbook synthesis.

### Data plane

- **Definition:** The runtime path that executes workload operations and carries workload data under control-plane intent.
- **Aliases:** Workload plane
- **Source key:** Handbook synthesis
- **Verification state:** Handbook synthesis
- **Notes:** Chapter 1 uses this bounded architectural term; Kubernetes documentation does not define a complete enterprise ML data plane.

### Training plane

- **Definition:** The execution boundary that transforms versioned code; configuration; and data references into candidate model artifacts plus training evidence.
- **Aliases:** None
- **Source key:** Handbook synthesis
- **Verification state:** Handbook synthesis
- **Notes:** This is a Chapter 1 decomposition for responsibility analysis rather than an industry-standard plane.

### Serving plane

- **Definition:** The execution boundary that loads an approved model artifact and returns batch; streaming; or online inference outputs with runtime telemetry.
- **Aliases:** Inference plane
- **Source key:** Handbook synthesis
- **Verification state:** Handbook synthesis
- **Notes:** This is a Chapter 1 decomposition. Workload-specific serving implementations are deferred to later chapters.

### Model registry

- **Definition:** A repository workflow for registered models and model versions with metadata such as aliases; tags; descriptions; source-run information; and creation timestamps.
- **Aliases:** None
- **Source key:** `MLFLOW-REGISTRY-2026`
- **Verification state:** Verified
- **Notes:** The feature set was rechecked against the pinned MLflow 3.15.1 registry workflow. A registry product is not by itself the full governance system of record.

### Artifact store

- **Definition:** Storage for large run outputs such as model weights and data files while run metadata remains in a backend store.
- **Aliases:** Artifact repository
- **Source key:** `MLFLOW-TRACKING-2026`
- **Verification state:** Verified
- **Notes:** The backend-store separation was rechecked against the pinned MLflow 3.15.1 tracking page. Other products may draw the boundary differently.

### Lineage

- **Definition:** Linked metadata that identifies pipeline and component versions; execution context; parameters; produced artifacts; model ancestry; and evaluation results across an ML lifecycle.
- **Aliases:** Provenance
- **Source key:** `GOOGLECLOUD-MLOPS-2024`
- **Verification state:** Verified
- **Notes:** The definition follows Google's predictive-ML metadata example. Build provenance is a narrower supply-chain record.

### Reproducibility

- **Definition:** The ability to recreate an ML artifact or result from recorded code; data references; configuration; dependencies; environment; and execution metadata within an explicitly stated tolerance.
- **Aliases:** Reproducible workflow
- **Source key:** Handbook synthesis
- **Verification state:** Handbook synthesis
- **Notes:** Exact identity may be infeasible for some training workloads; Chapter 1 must state the required tolerance and evidence boundary.

### Continuous training (CT)

- **Definition:** Automated retraining of a model in production pipelines in response to triggers with validation before a candidate proceeds toward serving.
- **Aliases:** CT
- **Source key:** `GOOGLECLOUD-MLOPS-2024`
- **Verification state:** Verified
- **Notes:** Continuous training creates and validates candidates within Google's predictive-ML pattern; it does not itself authorize production promotion. Expand CT at first use if used.

### Service-level indicator (SLI)

- **Definition:** A measurement of the level of service provided to users.
- **Aliases:** SLI
- **Source key:** `GOOGLE-SRESLO-2018`
- **Verification state:** Verified
- **Notes:** Record the measurement implementation and blind spots. Expand SLI at first use in each chapter.

### Service-level objective (SLO)

- **Definition:** A target level of service reliability measured by one or more service-level indicators.
- **Aliases:** SLO
- **Source key:** `GOOGLE-SRESLO-2018`
- **Verification state:** Verified
- **Notes:** A workload-specific objective requires stakeholder agreement and an owner. Expand SLO at first use in each chapter.

### Architecture decision record (ADR)

- **Definition:** A maintained record of an architecture decision; its context and assumptions; considered options; accepted trade-offs; evidence; owner; and review triggers.
- **Aliases:** ADR
- **Source key:** Handbook synthesis
- **Verification state:** Handbook synthesis
- **Notes:** This handbook-specific contract supports the Chapter 1 exercise. Expand ADR at first use in each chapter.

## Entry contract

Each controlled entry records a term; concise definition; aliases; source key; verification state; and scope note. Every external source key resolves to [the bibliography](sources/references.md). `Verified` is reserved for wording entailed by the cited source. `Handbook synthesis` identifies a local definition with its boundary stated in the notes.

## Changelog

### 2026-08-23

- Replaced the six-column controlled-term table with accessible per-term labeled blocks while preserving the `#controlled-terms` navigation target and every definition, source boundary, verification state, alias, and note.
- Pinned the Kubernetes-specific Control plane definition to v1.36 and its immutable official documentation revision.
- Rechecked the Model registry and Artifact store definitions against pinned MLflow 3.15.1 documentation and recorded that evidence boundary in their notes.
- Replaced all 14 pending definitions with source-entailing definitions or explicit handbook synthesis.
- Added stable bibliography keys; version and applicability boundaries; and acronym first-use instructions.
- Audited the stable `#controlled-terms` anchor and Chapter 1 first-use expansions during Task 7; no controlled definition or verification state changed.
