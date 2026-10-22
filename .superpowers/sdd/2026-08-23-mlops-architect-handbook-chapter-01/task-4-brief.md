### Task 4: Research Chapter 1 with parallel specialist agents

**Files:**

- Create: `mlops/architect-handbook/sources/research/chapter-01-foundations.md`
- Create: `mlops/architect-handbook/sources/research/chapter-01-governance-reliability.md`
- Create: `mlops/architect-handbook/sources/research/chapter-01-platform-strategy.md`

**Interfaces:**

- Consumes: Chapter 1 outline, evidence policy, and glossary contract from Task 3.
- Produces: three independent cited research reports whose source keys and claims are synthesized in Task 5.

- [ ] **Step 1: Dispatch three read-only research agents in parallel**

Use isolated contexts and one domain per agent:

1. **Foundations agent:** ML lifecycle, hidden technical debt, reproducibility, metadata, artifacts, feedback loops, and ML testing.
2. **Governance/reliability agent:** NIST AI RMF, security/governance plane, SLI/SLO boundaries, system-of-record integrity, and operational accountability.
3. **Platform-strategy agent:** platform/product ownership, Team Topologies/platform engineering concepts, build-versus-buy decision criteria, managed-service trade-offs, and Senior/Staff/Principal scope.

Each agent must search the live web, use only primary or authoritative sources for technical claims, read at least four key sources in full, and write its report to its assigned path. Each report must include methodology, exact source URLs, publication/update dates, accessed date `2026-08-23`, claim excerpts paraphrased in the agent's own words, applicability limits, unresolved conflicts, and a dated `## Changelog`. Agents must not edit any other file.

- [ ] **Step 2: Require the foundational source shortlist to be checked**

The research must attempt to verify and include or explicitly reject these sources:

- Sculley et al., *Hidden Technical Debt in Machine Learning Systems*
- Breck et al., *The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction*
- Google, *Rules of Machine Learning*
- NIST, *AI Risk Management Framework 1.0* and the current Playbook
- Google Cloud Architecture Center guidance on MLOps continuous delivery and automation pipelines
- AWS Well-Architected Machine Learning Lens
- Microsoft Azure Well-Architected Framework guidance for AI/ML workloads
- Kubernetes documentation for control-plane and workload concepts
- MLflow documentation for tracking and model-registry concepts
- CNCF or Linux Foundation platform-engineering guidance where it directly supports a claim

Sources that are obsolete, inaccessible, superseded, marketing-only, or unable to support the planned claim must be recorded as rejected with a reason.

- [ ] **Step 3: Review the three reports for source quality**

Confirm each report has at least four fully read authoritative sources, no bare search-result links, no unsourced quantitative claim, and explicit fact-versus-inference labeling. Send deficiencies back to the same agent for correction before Task 5.

- [ ] **Step 4: Update status and checkpoint**

Set Chapter 1 content state to `Researching`. Record report hashes and source counts in the execution ledger.

---

