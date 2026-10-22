# Chapter 1 Foundations: Research Report

**Research date:** 2026-08-23  
**Accessed date for every web source:** 2026-08-23  
**Scope:** Why production machine learning (ML) is a systems discipline; ML-specific technical debt; production-readiness testing; lifecycle and feedback-loop foundations; and bounded control-plane, workload, tracking, artifact, and registry concepts.  
**Confidence:** High for statements directly supported by the canonical papers and first-party documentation; medium for the architectural synthesis, which must be validated against the handbook's governance, reliability, and platform-strategy research.

## Methodology

The research answered five questions: (1) what makes production ML a systems problem, (2) which ML-specific dependencies create hidden debt, (3) what production readiness requires beyond offline model evaluation, (4) which feedback loops shape the lifecycle, and (5) which control and record boundaries are directly supported by Kubernetes and MLflow documentation.

Searches targeted canonical titles and official domains. Eight authoritative sources were read in full or, for documentation sites, across the complete substantive page content. Search snippets were discovery aids only. Claims below use one of two labels:

- **Sourced fact:** a close paraphrase entailed by the linked source.
- **Handbook synthesis:** an architectural inference assembled from cited facts and explicit assumptions; it is not an externally verified industry rule.

No production metric, benchmark, adoption rate, or cost estimate was inferred. Quantities appear only when the source itself defines them, such as the 28 checks in the ML Test Score paper.

## Findings

### Production ML is a systems discipline

**Sourced fact:** Sculley et al. argue that an ML system inherits conventional software maintenance concerns and adds system-level risks because data influences behavior. The paper identifies entanglement, unstable and underused data dependencies, hidden consumers, feedback loops, configuration debt, pipeline jungles, reproducibility debt, process debt, and changes in the external world. Its central boundary is the production system, not the model file. [Sculley et al., 2015](https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Sourced fact:** Breck et al. make the same boundary operational: training can be viewed as a compilation process whose inputs include code and training data, while the resulting model needs debugging, rollback, monitoring, and release controls comparable to those applied to a software binary. They also state that ordinary software-engineering controls remain necessary alongside ML-specific tests. [Breck et al., 2017](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)

**Handbook synthesis:** A Chapter 1 architecture should therefore treat model quality as one signal inside a larger production contract. The contract spans input semantics, feature computation, training code, configuration, artifacts, validation gates, deployment state, runtime behavior, consumers, and feedback data. A model can meet an offline threshold while the production system remains unready because one of those interfaces is unowned, unversioned, untested, or unobservable.

### Hidden technical debt is mostly boundary debt

**Sourced fact:** Model inputs are entangled: changing one feature, its distribution, a hyperparameter, a sampling choice, or another learning input can alter the influence of other inputs. Sculley et al. call this the CACE principle, meaning that an apparently local change can have non-local behavioral effects. The same paper warns that undeclared consumers and correction cascades silently couple otherwise separate systems. [Sculley et al., 2015](https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Sourced fact:** Data dependencies can be harder to discover than code dependencies. The paper recommends annotations, resolved dependency trees, access restrictions, interface agreements, and versioned copies of unstable signals as possible controls, while acknowledging that versioning introduces staleness and maintenance costs. [Sculley et al., 2015](https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Sourced fact:** The external world changes, so unit and end-to-end tests cannot by themselves demonstrate continuing fitness. Sculley et al. call for live monitoring and discuss prediction bias, action limits, upstream producer objectives, alert propagation, and automated response as starting points rather than a universal checklist. [Sculley et al., 2015](https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Handbook synthesis:** The useful architectural unit is a dependency edge with an owner and a change contract. For each edge, Chapter 1 should ask: Who produces it? Who consumes it? Which semantic invariant is promised? Which version or time boundary identifies it? How is incompatible change detected? Which fallback or rollback exists? Where does failure evidence appear?

### Production readiness needs balanced, automated evidence

**Sourced fact:** The ML Test Score paper proposes 28 checks divided across four areas: features and data, model development, ML infrastructure, and monitoring. Its score gives partial credit for documented manual execution, full credit for repeated automation, and takes the minimum of the four area totals so strength in one area does not mask weakness in another. [Breck et al., 2017](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)

**Sourced fact:** The paper's infrastructure checks include reproducibility, unit-tested model specifications, full-pipeline integration tests, pre-serving model validation, debuggability, canarying, and safe rollback. Its monitoring checks cover dependency changes, data invariants, training-serving skew, model staleness, numerical stability, compute regressions, and served prediction quality. [Breck et al., 2017](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)

**Sourced fact:** The rubric was based on decades of Google production-ML engineering and was later applied through structured interviews with 36 Google teams. The authors state that their dominant context was supervised learning with repeated training and low-latency serving, while noting that many checks also apply to other deployment patterns. They also report lower perceived applicability of some data tests for image and audio teams and gaps where labels are absent or expensive. [Breck et al., 2017](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)

**Handbook synthesis:** Use the paper as a diagnostic taxonomy, not as a universal compliance score. A production-readiness gate should preserve its balanced coverage while weighting local safety, regulatory, business, latency, and recovery risks. The evidence should record the test, scope, automation level, result, owner, freshness, and response rather than merely copying a numeric score.

### The lifecycle is iterative and observable

**Sourced fact:** Google's Rules of ML defines a pipeline as infrastructure that gathers data, creates training data, trains models, and exports them to production. It advises teams to establish metrics, build a solid end-to-end pipeline, begin with a simple model, test infrastructure independently, check models before export, watch for silent failures, and assign feature ownership and documentation. [Google, Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

**Sourced fact:** The guide treats deployment as iterative rather than terminal. It recommends designing for repeated launches, measuring model deltas, reusing feature logic where practical, monitoring training-serving skew, evaluating on data later than the training window, and accounting for feedback caused by ranking and presentation choices. [Google, Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

**Sourced fact:** Sculley et al. distinguish direct feedback, where model decisions affect future training-data selection, from hidden feedback, where separate systems influence each other indirectly through the world. [Sculley et al., 2015](https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Handbook synthesis:** A foundational lifecycle should be drawn as a loop, not a one-way train-and-deploy sequence:

`product event -> captured data -> validated dataset -> training run -> evaluated artifact -> approved reference -> deployed workload -> predictions/actions -> outcomes and telemetry -> product event`

The architecture must preserve both lineage direction and influence direction. Outcomes can become labels, model actions can change which outcomes are observed, and platform telemetry can trigger retraining, rollback, or human review. The synthesis does not imply that every system should retrain automatically.

### Control-plane and workload concepts

**Sourced fact:** Kubernetes v1.36 separates a control plane from worker nodes. The API server exposes the cluster API; etcd stores API data; the scheduler binds unscheduled Pods to nodes; controllers implement API behavior; and node components maintain running Pods and container execution. [Kubernetes Components, modified 2026-05-30](https://kubernetes.io/docs/concepts/overview/components/) ([immutable official source revision](https://github.com/kubernetes/website/blob/6e5065edcfd577d59c7c9ee18b238ecbc91675fe/content/en/docs/concepts/overview/components.md))

**Sourced fact:** Kubernetes v1.36 controllers observe resource state and act to move current state toward the desired state represented in resource specifications. Controllers report state through the API server, and Kubernetes favors multiple focused controllers over a single monolithic loop. [Kubernetes Controllers, modified 2024-09-01](https://kubernetes.io/docs/concepts/architecture/controller/) ([immutable official source revision](https://github.com/kubernetes/website/blob/7e64c2db8236a6b7325cf82ec050783a1b0a3850/content/en/docs/concepts/architecture/controller.md))

**Sourced fact:** Kubernetes v1.36 defines a workload as an application running in Pods and provides higher-level workload resources whose controllers maintain the specified set of Pods. Jobs and CronJobs cover run-to-completion tasks, while Deployments and StatefulSets cover other execution semantics. [Kubernetes Workloads, modified 2026-04-27](https://kubernetes.io/docs/concepts/workloads/) ([immutable official source revision](https://github.com/kubernetes/website/blob/af5b13e33446de715819ed64e0d45085c70c1bf5/content/en/docs/concepts/workloads/_index.md))

**Handbook synthesis:** The transferable control-plane pattern is `declared intent -> authoritative state -> reconciliation -> observed status -> corrective action`. Applied to ML, this pattern can inform training jobs, validation gates, deployment references, and rollback workflows. Kubernetes documentation supports the orchestration analogy; it does not establish Kubernetes as the owner of data semantics, experiment lineage, model approval, or business risk.

### Metadata, artifacts, and model references

**Sourced fact:** In MLflow 3.15.1 tracking, a run records metadata such as parameters, metrics, and timing plus output artifacts. Experiments group runs and models; dataset metadata can be associated with training events; a backend store persists run metadata; and an artifact store persists large outputs such as model weights and data files. [MLflow 3.15.1 Tracking](https://mlflow.org/docs/3.15.1/ml/tracking/)

**Sourced fact:** MLflow 3.15.1's Model Registry workflow supports registered models, versions, aliases, tags, descriptions, source-run information, and creation timestamps. Aliases are mutable named references to model versions. Fixed model stages were deprecated as of MLflow 2.9.0 in favor of tags, aliases, and separated environments. [MLflow 3.15.1 Model Registry Workflow](https://mlflow.org/docs/3.15.1/ml/model-registry/workflow/)

**Handbook synthesis:** Tracking metadata, artifact storage, model registration, and deployment state are different record classes even when one product exposes them together. A sound architecture identifies the authority for each class and records immutable identities beneath mutable convenience references. A mutable alias can simplify promotion, but an audit or rollback decision should resolve the alias to the exact model version and deployment revision observed at decision time.

## Architecture implications for Chapter 1

| Boundary | Evidence-backed concern | Chapter treatment |
| --- | --- | --- |
| Data producer -> feature pipeline | Silent semantic change, staleness, privacy, hidden consumers | Define owner, schema/invariant, version or event-time boundary, notification path, and deletion behavior. |
| Feature pipeline -> training | Training-serving skew and untested feature logic | Require parity evidence, sampled comparison, or a documented alternative appropriate to the serving pattern. |
| Training -> model artifact | Non-determinism, unaudited configuration, weak reproducibility | Record code/configuration identity, data reference, environment, run metadata, and reproducibility tolerance. |
| Model artifact -> approval | Offline quality can mask slice, compatibility, or policy failures | Use multiple gates: data, model, infrastructure, safety/governance, and operational recovery. |
| Approved reference -> serving workload | Mutable reference, incompatible runtime, unsafe rollout | Resolve immutable version, test load/serve compatibility, canary where suitable, and retain rollback evidence. |
| Serving -> observed outcomes | Delayed labels, feedback loops, silent degradation | Separate service telemetry, data-quality signals, model behavior, product outcomes, and intervention triggers. |

Every row is **Handbook synthesis** based on the cited findings above. The controls are questions for architecture review, not claims that one implementation fits every workload.

## Applicability limits

- The Sculley paper is canonical practitioner literature from Google in 2015. Its debt taxonomy remains useful, but its examples and tool context predate contemporary managed platforms, foundation models, and agentic systems.
- The ML Test Score reflects Google production experience reported in 2017, centered on supervised, repeatedly trained systems. It is not a formal standard, regulatory framework, or proof of safety.
- Rules of ML is first-party practitioner guidance, last updated 2025-08-25. Product examples illustrate Google experience and should not be converted into universal frequency, scale, or benefit claims.
- Kubernetes documentation supports Kubernetes v1.36 behavior as accessed on 2026-08-23. The human-readable pages are paired above with immutable official `kubernetes/website` revision permalinks; later releases require a new snapshot review.
- MLflow documentation supports claims about MLflow 3.15.1 behavior as accessed on 2026-08-23. The report pins the behavior pages to 3.15.1 and retains the 2026-08-02 release record in the source register.
- Exact reproducibility may be infeasible for some parallel or non-convex training. Architecture should specify a bounded reproducibility target and evidence sufficient for diagnosis, audit, and rollback.

## Conflicts and unresolved questions

1. **Exact reproducibility versus operational repeatability.** Breck et al. describe identical retraining as an ideal; Sculley et al. emphasize sources of unavoidable non-determinism. Resolution: distinguish bitwise/model identity from bounded metric, prediction, lineage, and environment reproducibility. The acceptable tolerance remains workload-specific.
2. **Equal-weight rubric versus risk-based gates.** The ML Test Score intentionally gives checks equal value and uses the weakest area. Enterprise architecture may need non-equal blocking controls for safety or regulation. This report retains the rubric as a coverage model and leaves gate weighting to governance research.
3. **Mutable aliases versus immutable audit evidence.** MLflow documents aliases as reassignable references. It does not state that alias history alone is sufficient for audit or rollback. The immutable-resolution requirement above is handbook synthesis and needs implementation-specific validation.
4. **Control-plane analogy versus product boundary.** Kubernetes reconciles cluster resource state; MLflow records experiments and model lifecycle metadata. Neither source defines a complete enterprise ML control plane. Chapter 1 must state which authority owns code, data, artifacts, approvals, deployment, telemetry, and policy.
5. **Feedback response policy.** The papers support monitoring and identify feedback risks, but they do not establish a universal trigger for retraining, rollback, shutdown, or human review. Those thresholds remain explicit architecture decisions.

## Source decisions

### Accepted and fully read

| Key | Source and exact URL | Publication or update date | Why accepted |
| --- | --- | --- | --- |
| SCULLEY-2015 | [Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf) | NeurIPS 2015 | Canonical peer-reviewed systems-debt taxonomy; direct PDF read across all nine pages. |
| BRECK-2017 | [The ML Test Score](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf) | IEEE Big Data 2017 | Primary paper defining the 28-check rubric, scoring method, context, and limitations; direct PDF read across all ten pages. |
| GOOGLE-RULES-ML | [Rules of Machine Learning](https://developers.google.com/machine-learning/guides/rules-of-ml) | Last updated 2025-08-25 UTC | First-party lifecycle and ML engineering guidance; all 43 rules and page notes reviewed. |
| K8S-COMPONENTS | [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/) ([immutable official revision](https://github.com/kubernetes/website/blob/6e5065edcfd577d59c7c9ee18b238ecbc91675fe/content/en/docs/concepts/overview/components.md)) | Kubernetes v1.36; page last modified 2026-05-30 | First-party definition of control-plane and node-component responsibilities. |
| K8S-CONTROLLERS | [Kubernetes Controllers](https://kubernetes.io/docs/concepts/architecture/controller/) ([immutable official revision](https://github.com/kubernetes/website/blob/7e64c2db8236a6b7325cf82ec050783a1b0a3850/content/en/docs/concepts/architecture/controller.md)) | Kubernetes v1.36; page last modified 2024-09-01 | First-party description of desired state, current state, and reconciliation loops. |
| K8S-WORKLOADS | [Kubernetes Workloads](https://kubernetes.io/docs/concepts/workloads/) ([immutable official revision](https://github.com/kubernetes/website/blob/af5b13e33446de715819ed64e0d45085c70c1bf5/content/en/docs/concepts/workloads/_index.md)) | Kubernetes v1.36; page last modified 2026-04-27 | First-party workload and controller semantics, including run-to-completion tasks. |
| MLFLOW-TRACKING | [MLflow Tracking](https://mlflow.org/docs/3.15.1/ml/tracking/) and [MLflow 3.15.1 release](https://mlflow.org/releases/3.15.1/) | Version 3.15.1 released 2026-08-02; page update date unavailable | First-party definitions of runs, experiments, metadata, artifacts, datasets, and storage boundaries. |
| MLFLOW-REGISTRY | [MLflow Model Registry Workflow](https://mlflow.org/docs/3.15.1/ml/model-registry/workflow/) and [MLflow 3.15.1 release](https://mlflow.org/releases/3.15.1/) | Version 3.15.1 released 2026-08-02; page update date unavailable | First-party registry, version, tag, alias, environment, and stage-deprecation behavior. |

### Rejected or deferred candidates

| Candidate | Decision | Reason |
| --- | --- | --- |
| [NeurIPS abstract page for Sculley et al.](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html) | Rejected as claim evidence | Authoritative but too thin for debt mechanisms and limitations; the proceedings PDF supersedes it for this report. |
| [Google Research publication page for Breck et al.](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/) | Rejected as claim evidence | Useful metadata and abstract, but it omits the tests, scoring mechanics, study context, and caveats available in the direct paper. |
| Third-party summaries, blogs, forum posts, and Wikipedia results | Rejected | They add no authority over the canonical papers or first-party documentation and create paraphrase drift. |
| NIST AI RMF, cloud-provider MLOps architecture guides, well-architected ML guidance, and platform-engineering sources | Deferred to sibling reports | Authoritative and relevant to governance, reliability, and platform strategy, but outside this foundations agent's assigned boundary. Their absence here is not a rejection of their handbook value. |
| MLflow stage-based examples without deprecation context | Rejected for forward guidance | Official documentation states that fixed stages were deprecated as of MLflow 2.9.0; tags, aliases, and separated environments are the supported direction in the reviewed workflow. |

## Changelog

### 2026-08-23

- Corrected the ML Test Score provenance boundary: Google engineering experience informed the rubric and structured interviews applied it to 36 Google teams.
- Pinned all MLflow behavior links to 3.15.1 and retained the 2026-08-02 release record.
- Pinned Kubernetes behavior to v1.36 and paired each readable page with an immutable official `kubernetes/website` revision.
- Created the Chapter 1 foundations research report from eight accepted authoritative sources.
- Documented source methodology, fact-versus-synthesis labels, applicability limits, unresolved conflicts, and source acceptance decisions.
- Added bounded Kubernetes control-loop and MLflow record-boundary concepts without treating either product as a complete MLOps control plane.
