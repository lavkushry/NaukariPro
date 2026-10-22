# References

## Bibliography status

This bibliography admits the authoritative sources reviewed for Chapter 1. A source key identifies the cited publication or version snapshot; it does not broaden the supported scope stated for that entry.

## Source-key convention

Keys use uppercase `ORG-SHORTTITLE-YEAR` form. The year identifies the publication or reviewed snapshot. Chapter prose and `claim-ledger.csv` must use these keys exactly.

## Authoritative bibliography

### `SCULLEY-TECHDEBT-2015`

- **Title:** *Hidden Technical Debt in Machine Learning Systems*
- **Author or organization:** D. Sculley; Gary Holt; Daniel Golovin; Eugene Davydov; Todd Phillips; Dietmar Ebner; Vinay Chaudhary; Michael Young; Jean-Francois Crespo; Dan Dennison
- **Publication or update date:** 2015
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://papers.nips.cc/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf>
- **Version:** NeurIPS 2015 proceedings paper
- **Source class:** Peer-reviewed canonical technical literature
- **Supported scope:** Supports the production-system boundary; ML-specific technical-debt mechanisms; data dependencies; feedback loops; monitoring need; and stated limits on reproducibility.

### `BRECK-MLTESTSCORE-2017`

- **Title:** *The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction*
- **Author or organization:** Eric Breck; Shanqing Cai; Eric Nielsen; Michael Salib; D. Sculley
- **Publication or update date:** 2017
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf>
- **Version:** IEEE Big Data 2017 paper
- **Source class:** Peer-reviewed canonical technical literature
- **Supported scope:** Supports the 28-check production-readiness rubric; its four areas; scoring mechanics; operational test categories; study context; and stated applicability limits.

### `GOOGLE-RULESML-2025`

- **Title:** *Rules of Machine Learning*
- **Author or organization:** Google for Developers
- **Publication or update date:** 2025-08-25
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://developers.google.com/machine-learning/guides/rules-of-ml>
- **Version:** Page updated 2025-08-25 UTC
- **Source class:** First-party practitioner guidance
- **Supported scope:** Supports Google's pipeline definition and guidance on metrics; end-to-end infrastructure; independent infrastructure tests; pre-export checks; repeated launches; skew monitoring; and feedback effects.

### `KUBERNETES-COMPONENTS-2026`

- **Title:** *Kubernetes Components*
- **Author or organization:** The Kubernetes Authors
- **Publication or update date:** 2026-05-30
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** Human-readable page <https://kubernetes.io/docs/concepts/overview/components/>; immutable official source revision <https://github.com/kubernetes/website/blob/6e5065edcfd577d59c7c9ee18b238ecbc91675fe/content/en/docs/concepts/overview/components.md>
- **Version:** Kubernetes v1.36; page modified 2026-05-30; source revision `6e5065edcfd577d59c7c9ee18b238ecbc91675fe`
- **Source class:** First-party product documentation
- **Supported scope:** Supports the Kubernetes control-plane and worker-node separation plus the documented responsibilities of the API server; etcd; scheduler; controllers; and node components.

### `KUBERNETES-CONTROLLERS-2024`

- **Title:** *Controllers*
- **Author or organization:** The Kubernetes Authors
- **Publication or update date:** 2024-09-01
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** Human-readable page <https://kubernetes.io/docs/concepts/architecture/controller/>; immutable official source revision <https://github.com/kubernetes/website/blob/7e64c2db8236a6b7325cf82ec050783a1b0a3850/content/en/docs/concepts/architecture/controller.md>
- **Version:** Kubernetes v1.36; page modified 2024-09-01; source revision `7e64c2db8236a6b7325cf82ec050783a1b0a3850`
- **Source class:** First-party product documentation
- **Supported scope:** Supports the Kubernetes reconciliation model in which controllers observe resource state and act toward desired state through focused control loops.

### `KUBERNETES-WORKLOADS-2026`

- **Title:** *Workloads*
- **Author or organization:** The Kubernetes Authors
- **Publication or update date:** 2026-04-27
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** Human-readable page <https://kubernetes.io/docs/concepts/workloads/>; immutable official source revision <https://github.com/kubernetes/website/blob/af5b13e33446de715819ed64e0d45085c70c1bf5/content/en/docs/concepts/workloads/_index.md>
- **Version:** Kubernetes v1.36; page modified 2026-04-27; source revision `af5b13e33446de715819ed64e0d45085c70c1bf5`
- **Source class:** First-party product documentation
- **Supported scope:** Supports the Kubernetes workload definition and the documented execution semantics of Pods; Jobs; CronJobs; Deployments; and StatefulSets.

### `MLFLOW-TRACKING-2026`

- **Title:** *MLflow Tracking*
- **Author or organization:** MLflow Project
- **Publication or update date:** 2026-08-02 release context; page date not stated
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://mlflow.org/docs/3.15.1/ml/tracking/>; release record <https://mlflow.org/releases/3.15.1/>
- **Version:** MLflow 3.15.1
- **Source class:** First-party product documentation and release record
- **Supported scope:** Supports MLflow 3.15.1 run; experiment; dataset-metadata; backend-store; artifact-store; and tracking-boundary behavior.

### `MLFLOW-REGISTRY-2026`

- **Title:** *Model Registry Workflows*
- **Author or organization:** MLflow Project
- **Publication or update date:** 2026-08-02 release context; page date not stated
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://mlflow.org/docs/3.15.1/ml/model-registry/workflow/>; release record <https://mlflow.org/releases/3.15.1/>
- **Version:** MLflow 3.15.1
- **Source class:** First-party product documentation and release record
- **Supported scope:** Supports MLflow 3.15.1 registered-model; version; alias; tag; description; source-run; timestamp; and fixed-stage deprecation behavior.

### `NIST-AIRMF-2023`

- **Title:** *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*
- **Author or organization:** National Institute of Standards and Technology
- **Publication or update date:** 2023-01-26
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://doi.org/10.6028/NIST.AI.100-1>; direct PDF <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf>
- **Version:** NIST AI 100-1; AI RMF 1.0
- **Source class:** Government framework
- **Supported scope:** Supports voluntary and outcome-focused AI-risk governance; lifecycle accountability; inventories; testing and evaluation; monitoring; third-party risk; incident response; residual risk; and retirement.

### `NIST-SP80053R5-2025`

- **Title:** *Security and Privacy Controls for Information Systems and Organizations*
- **Author or organization:** Joint Task Force; National Institute of Standards and Technology
- **Publication or update date:** Rev. 5 published 2020-12-10; Release 5.2.0 issued 2025-08-27
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://doi.org/10.6028/NIST.SP.800-53r5>; publication page <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final>; immutable official OSCAL control catalog <https://github.com/usnistgov/oscal-content/blob/78650f02ad9321bb7b817846f8fbd4f2bcd620de/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json>
- **Version:** NIST SP 800-53 Rev. 5; electronic control catalog Release 5.2.0; source revision `78650f02ad9321bb7b817846f8fbd4f2bcd620de`
- **Source class:** Government security and privacy control catalog
- **Supported scope:** Supports the existence and bounded wording of controls for account management; identification and authentication; access enforcement; least privilege; event logging; audit-information protection; cryptographic protection; transmission and storage confidentiality; system backup and recovery; process isolation; and software and information integrity. The catalog requires organizational selection and tailoring and does not make every control a universal baseline.

### `NIST-AIRMFSTATUS-2026`

- **Title:** *AI Risk Management Framework Program Page*
- **Author or organization:** National Institute of Standards and Technology
- **Publication or update date:** Page date not stated; status observed 2026-08-23
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://www.nist.gov/itl/ai-risk-management-framework>
- **Version:** Status snapshot accessed 2026-08-23
- **Source class:** First-party government status page
- **Supported scope:** Supports only the observed revision status of AI RMF 1.0 and related NIST publication records on the access date.

### `NIST-AIRMFPLAYBOOK-2023`

- **Title:** *NIST AI RMF Playbook*
- **Author or organization:** National Institute of Standards and Technology
- **Publication or update date:** Initial release 2023-01; PDF added 2023-08
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://airc.nist.gov/airmf-resources/playbook/>; direct PDF <https://airc.nist.gov/docs/AI_RMF_Playbook.pdf>
- **Version:** Living Playbook aligned to AI RMF 1.0; no document revision identifier exposed
- **Source class:** First-party government implementation guidance
- **Supported scope:** Supports optional implementation actions for risk tiers; approval paths; monitoring; evidence retention; third-party components; response; recovery; and decommissioning.

### `NIST-PLAYBOOKAUDIT-2023`

- **Title:** *Playbook Audit Log*
- **Author or organization:** National Institute of Standards and Technology
- **Publication or update date:** Last listed entry 2023-08
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://airc.nist.gov/airmf-resources/playbook/audit-log/>
- **Version:** Visible audit-log snapshot accessed 2026-08-23
- **Source class:** First-party government provenance record
- **Supported scope:** Supports only the visible dates and change-history provenance for the NIST AI RMF Playbook.

### `GOOGLE-SRESLO-2018`

- **Title:** *Implementing SLOs*
- **Author or organization:** Google Site Reliability Engineering
- **Publication or update date:** 2018 copyright; chapter revision date not stated
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://sre.google/workbook/implementing-slos/>
- **Version:** Site Reliability Workbook chapter
- **Source class:** First-party practitioner guidance
- **Supported scope:** Supports service-level indicator and service-level objective definitions; user-centric measurements; dependency boundaries; ownership; written error-budget policy; response actions; and review practice.

### `GOOGLECLOUD-MLOPS-2024`

- **Title:** *MLOps: Continuous Delivery and Automation Pipelines in Machine Learning*
- **Author or organization:** Google Cloud Architecture Center
- **Publication or update date:** 2024-08-28
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning>
- **Version:** Page reviewed and updated 2024-08-28 UTC
- **Source class:** First-party cloud architecture guidance
- **Supported scope:** Supports Google's predictive-ML automation levels; CI/CD and continuous-training boundaries; validation; promotion; metadata; monitoring; lineage; reproducibility; and rollback context.

### `SLSA-BUILD-2026`

- **Title:** *SLSA v1.2 Specification and Build Requirements*
- **Author or organization:** Supply-chain Levels for Software Artifacts project under OpenSSF
- **Publication or update date:** Publication date not stated; specification accessed 2026-08-23
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://slsa.dev/spec/v1.2/>; build requirements <https://slsa.dev/spec/v1.2/build-requirements>
- **Version:** SLSA v1.2
- **Source class:** Official supply-chain security specification
- **Supported scope:** Supports build-provenance digest binding; authenticity; control-plane generation; hosted-build and isolation requirements; producer versus platform responsibilities; and the Build track's artifact scope.

### `SLSA-VERIFICATION-2026`

- **Title:** *Build: Verifying Artifacts*
- **Author or organization:** Supply-chain Levels for Software Artifacts project under OpenSSF
- **Publication or update date:** Publication date not stated; SLSA v1.2 documentation accessed 2026-08-23
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://slsa.dev/spec/v1.2/verifying-artifacts>; immutable official source revision <https://github.com/slsa-framework/slsa/blob/ae7fc76215004e8fae250c877eff8919bf048e3b/spec/verifying-artifacts.md?plain=1>
- **Version:** SLSA v1.2; source revision `ae7fc76215004e8fae250c877eff8919bf048e3b`
- **Source class:** Official supply-chain security specification
- **Supported scope:** Supports checking the provenance-envelope signature; matching the statement subject to the artifact digest; checking the provenance predicate type; and comparing provenance against consumer expectations. It does not state that signing alone reduces attack paths or establishes model validity.

### `AWS-MLLENS-2025`

- **Title:** *Machine Learning Lens*
- **Author or organization:** Amazon Web Services
- **Publication or update date:** 2025-11-19
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html>
- **Version:** AWS Well-Architected Machine Learning Lens published 2025-11-19
- **Source class:** First-party vendor architecture guidance
- **Supported scope:** Supports the lens audience; predictive-ML scope; and its separation from AWS generative-AI guidance only.

### `AWS-MLDESIGN-2025`

- **Title:** *Well-Architected Machine Learning Design Principles*
- **Author or organization:** Amazon Web Services
- **Publication or update date:** 2025-11-19 lens context; page date not stated
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/design-principles.html>
- **Version:** AWS Well-Architected Machine Learning Lens published 2025-11-19
- **Source class:** First-party vendor architecture guidance
- **Supported scope:** Supports AWS guidance on ownership; protection; resiliency; reusability; reproducibility; automation; resource trade-offs; cost awareness; and continuous improvement.

### `AWS-BUILDBUY-2025`

- **Title:** *MLCOST02-BP02 Perform a Tradeoff Analysis Between Custom and Pre-trained Models*
- **Author or organization:** Amazon Web Services
- **Publication or update date:** 2025-11-19 lens context; page date not stated
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost02-bp02.html>
- **Version:** AWS Well-Architected Machine Learning Lens published 2025-11-19
- **Source class:** First-party vendor architecture guidance
- **Supported scope:** Supports AWS's stated comparison factors for custom; pre-trained; transfer-learning; and fine-tuning options without supporting a universal selection outcome.

### `AWS-MANAGEDSERVICES-2025`

- **Title:** *MLCOST01-BP02 Use Managed Services to Reduce Total Cost of Ownership (TCO)*
- **Author or organization:** Amazon Web Services
- **Publication or update date:** 2025-11-19 lens context; page date not stated
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlcost01-bp02.html>
- **Version:** AWS Well-Architected Machine Learning Lens published 2025-11-19
- **Source class:** First-party vendor architecture guidance
- **Supported scope:** Supports AWS's stated lifecycle-cost inputs and managed-service position; it does not support a workload-neutral comparative cost conclusion.

### `MICROSOFT-AIWORKLOADS-2026`

- **Title:** *AI Workloads on Azure*
- **Author or organization:** Microsoft
- **Publication or update date:** 2026-05-07
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://learn.microsoft.com/en-us/azure/well-architected/ai/get-started>
- **Version:** Page updated 2026-05-07
- **Source class:** First-party vendor architecture guidance
- **Supported scope:** Supports Microsoft's stated SaaS; platform-as-a-service; and custom evaluation factors plus the page's declared workload exclusions.

### `MICROSOFT-WORKLOADS-2025`

- **Title:** *Azure Well-Architected Framework Workloads*
- **Author or organization:** Microsoft
- **Publication or update date:** 2025-08-12
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://learn.microsoft.com/en-us/azure/well-architected/workloads>
- **Version:** Page updated 2025-08-12
- **Source class:** First-party vendor architecture guidance
- **Supported scope:** Supports Microsoft's workload definition; workload-team and centralized-team responsibilities; shared obligations; constraints; service expectations; budgets; and change communication.

### `CNCF-PLATFORMS-2023`

- **Title:** *CNCF Platforms White Paper*
- **Author or organization:** CNCF TAG App Delivery Platforms Working Group
- **Publication or update date:** Version 1 completed 2023-03; web edition maintained
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://tag-app-delivery.cncf.io/whitepapers/platforms/>; version record <https://github.com/cncf/tag-app-delivery/blob/main/platforms-whitepaper/README.md>
- **Version:** Version 1 completed March 2023
- **Source class:** Authoritative industry working-group publication
- **Supported scope:** Supports platform-as-product; self-service; user research; optional and composable capabilities; capability-provider boundaries; and a thin integration layer for cloud-native delivery.

### `TEAMTOPOLOGIES-TVP-2019`

- **Title:** *What Is a Thinnest Viable Platform (TVP)?*
- **Author or organization:** Team Topologies authors
- **Publication or update date:** Published 2019-11-07; modified 2024-06-01
- **Accessed date:** 2026-08-23
- **Stable URL or DOI:** <https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp>
- **Version:** Page modified 2024-06-01
- **Source class:** First-party practitioner guidance
- **Supported scope:** Supports guidance to keep a thinnest viable platform no thicker than necessary; the example of a wiki page naming an approved cloud provider and services plus usage guidance; and attention to developer experience with stream-aligned teams as customers.

## Scope exclusions

- Vendor sources establish that vendor's documented model or position. They do not establish cross-vendor cost; reliability; security; or product superiority.
- `NIST-AIRMFSTATUS-2026` and `NIST-PLAYBOOKAUDIT-2023` support status and provenance only.
- `SLSA-BUILD-2026` supports artifact-build integrity. It does not establish dataset suitability; model validity; or deployment approval.
- `NIST-SP80053R5-2025` is a tailorable control catalog. Chapter recommendations using it must state system assumptions and must not present the entire catalog as a universal baseline.
- `SLSA-VERIFICATION-2026` supports artifact and provenance verification within SLSA's Build scope. It does not establish data semantics; model acceptance; or release authorization.
- Product documentation is version-scoped and must be reviewed by the claim-ledger deadline before publication use.

## Changelog

### 2026-08-23

- Replaced the movable SLSA `releases/v1.2` branch link with immutable official source revision `ae7fc76215004e8fae250c877eff8919bf048e3b` while retaining the official versioned SLSA page.
- Pinned Kubernetes behavior to v1.36; retained readable documentation; and added immutable official `kubernetes/website` source revisions.
- Added NIST SP 800-53 Rev. 5 Release 5.2.0 and SLSA v1.2 artifact-verification entries for bounded security-control evidence.
- Pinned both MLflow records to versioned 3.15.1 documentation URLs.
- Corrected the Team Topologies key to its 2019 publication year; added the 2024 modification date; and narrowed the supported scope to the page's stated guidance.
- Replaced the empty scaffold with 23 reviewed authoritative entries and stable uppercase source keys.
- Added complete bibliographic metadata; source classes; supported-scope statements; volatility boundaries; and vendor applicability limits.
