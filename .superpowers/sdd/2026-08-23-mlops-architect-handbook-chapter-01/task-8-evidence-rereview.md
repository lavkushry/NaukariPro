# Task 8 Focused Evidence Rereview

## Verdict

**APPROVED.** The focused rereview found **0 Critical, 0 Important, and 1 Minor** finding. All five Important findings from the first evidence review are closed, and the former Minor marker-scan finding is closed for maintained content. The remaining Minor bibliography-label defect does not weaken citation entailment or the stable versioned evidence path and does not block approval under the Task 8 gate.

Chapter 1 must nevertheless remain in its recorded `Technical Review` lifecycle state until the separate technical, editorial, diagram, and publication gates advance it. This report approves only the evidence rereview boundary.

## Scope and method

The rereview read the prior evidence review, evidence correction report, later technical and editorial correction reports, all three live research reports, all 72 live claim-ledger rows, all 25 bibliography entries, the complete glossary, the complete 710-line Chapter 1, its claim-coverage appendix, editorial status, all four live diagram sources and their registry text alternatives, and the complete Task 8 review-package diff. The earlier Task 4 and Task 5 reviews, design and evidence rules, style guide, repository instructions, and ECC deep-research evidence hierarchy remained part of the review baseline.

Every changed factual, normative, security, product, provider, and quantitative statement was checked independently against its ledger row and the cited primary or first-party source. Live checks covered the ML Test Score paper; Kubernetes documentation and pinned source commits; MLflow 3.15.1 documentation and release record; NIST AI RMF status; NIST SP 800-53 Rev. 5 Release 5.2.0 and its pinned OSCAL catalog; SLSA v1.2 Build verification; Team Topologies page metadata and wording; and the cited AWS, Microsoft, and CNCF provider-responsibility inputs.

## Prior-finding closure

| Prior finding | Result | Rereview evidence |
| --- | --- | --- |
| I1 — ML Test Score interview provenance | **Closed** | `sources/research/chapter-01-foundations.md:45` now distinguishes the rubric's basis in Google production-ML experience from its later application through structured interviews with 36 Google teams. That boundary matches the paper and the corrected `CH01-C009`. |
| I2 — Team Topologies wording and dates | **Closed** | `sources/research/chapter-01-platform-strategy.md:53,75` now uses the page's “no thicker than necessary” and wiki-page example, with `datePublished=2019-11-07` and `dateModified=2024-06-01` confirmed in first-party metadata. The source key is consistently `TEAMTOPOLOGIES-TVP-2019`. |
| I3 — moving MLflow links | **Closed** | All retained behavior links use `/docs/3.15.1/`; the source register and bibliography retain the 2026-08-02 MLflow 3.15.1 release record. The pinned tracking and registry pages entail `CH01-C018-C021` and the two sourced glossary definitions. No `/docs/latest/` MLflow evidence remains. |
| I4 — Kubernetes release and immutable evidence | **Closed** | `CH01-C014-C017`, the bibliography, foundations report, chapter, and Control plane glossary note are pinned to Kubernetes v1.36. The three source revisions resolve and entail the claims: `6e5065edcfd577d59c7c9ee18b238ecbc91675fe`, `7e64c2db8236a6b7325cf82ec050783a1b0a3850`, and `af5b13e33446de715819ed64e0d45085c70c1bf5`. The P1 review deadline remains 2026-11-21. |
| I5 — unledgered security requirements | **Closed** | The chapter now treats controls as tailored candidates or bounded architecture recommendations, states workload and risk assumptions, denies universal effectiveness, preserves SLSA Build scope, and labels repeated syntheses at point of use or within an explicit bounded region. `CH01-C066-C069` supply the verified P0 facts; `CH01-C070-C071` qualify the local control compositions. The NIST catalog contains AC-2, AC-3, AC-6, IA-2, AU-2, AU-9, SC-8, SC-13, SC-28, SC-39, SI-7, CP-9, and CP-10. SLSA v1.2 directly requires signature, subject-digest, predicate-type, and expectation checks. |
| M1 — marker-scan false positives | **Closed for maintained content** | The required maintained scan with `--glob '!**/scripts/**'` returns no matches. The ordinary research-report collision was reworded. The historical plan form with `--glob '!scripts/**'` still prints only nested script implementation/fixture literals because that pattern does not exclude `mlops/architect-handbook/scripts/**`; these are not unresolved maintained-content markers. |

## New and changed evidence

`CH01-C066-C072` are sequential, non-empty, uniquely keyed, and semantically aligned with their point-of-use prose:

- `CH01-C066-C069` are P0 `verified` rows. Their 2027-02-19 review dates correctly apply the 180-day security-evidence interval from the 2026-08-23 access date.
- `CH01-C070-C072` are P2 `qualified` architectural syntheses. Their assumptions, non-universality, provider-contract limitation, and SLSA scope are explicit; their annual review dates are 2027-08-23.
- NIST's official page confirms that Release 5.2.0 was issued on 2025-08-27. The pinned OSCAL catalog identifies version 5.2.0 and contains the named controls. No control-presence claim is converted into a universal baseline or effectiveness outcome.
- The SLSA verification page entails signature verification, artifact/statement subject-digest matching, `predicateType` checking, and comparison with consumer expectations. Chapter synthesis correctly adds policy admission as a local architecture decision and explicitly denies data-semantics, model-validity, and release-authorization scope.
- `CH01-C072` is correctly `qualified`, not `verified`: AWS, Microsoft, and CNCF provide the operating-boundary, shared-responsibility, support/change/observability, and capability-provider inputs, while the chapter limits the complete provider-duty allocation to obligations actually established by service documentation and contract terms.

The later technical and editorial edits add architecture clarification, fictional recovery mechanics, provider-contract detail, accessibility text, and evaluation artifacts. They do not introduce a new external fact, product promise, security effectiveness result, comparative outcome, or invented production metric. New recommendations sit inside explicit handbook-synthesis, illustrative, role-model, reference-flow, or exercise boundaries.

The only quantitative production-readiness facts remain the primary-source 28 checks and 36 Google teams. The chapter's three teams, two environments, two-quarter migration, twelve-month evidence period, and one-hour recovery target are explicitly invented exercise values. No unsupported measured benefit, price, workload scale, incident frequency, or provider guarantee appears.

## Findings

### Critical

None.

### Important

None.

### Minor

#### M1. The SLSA bibliography mislabels a movable release branch as immutable

Evidence:

- `mlops/architect-handbook/sources/references.md:195` calls `https://github.com/slsa-framework/slsa/blob/releases/v1.2/spec/verifying-artifacts.md?plain=1` an “immutable official version branch.”
- GitHub exposes `releases/v1.2` as `refs/heads/releases/v1.2`, currently resolving to `ae7fc76215004e8fae250c877eff8919bf048e3b`. A branch reference is movable; its current head itself records a 2026-04-14 link-fix commit, demonstrating maintained branch semantics.
- The adjacent official versioned URL `https://slsa.dev/spec/v1.2/verifying-artifacts` is live and fully entails `CH01-C069`. Therefore the false descriptor does not invalidate the claim, source class, version, risk, status, deadline, or chapter citation.

Concrete fix: replace the branch URL with `https://github.com/slsa-framework/slsa/blob/ae7fc76215004e8fae250c877eff8919bf048e3b/spec/verifying-artifacts.md?plain=1`, call it an immutable official source revision, and record that revision in the Version field. Alternatively, remove the immutability claim and retain only the official versioned SLSA URL.

## Reconciliation and validation evidence

| Check | Observed result |
| --- | --- |
| Ledger structure | 72 rows; 13 non-empty fields; sequential `CH01-C001-C072`; unique IDs; no unresolved source key |
| Risk/status | P0: 18 verified; P1: 28 verified; P2: 14 verified and 12 qualified; total verified: 60; total qualified: 12 |
| High-risk gate | All 46 P0/P1 rows are `verified`; no deadline is overdue on 2026-08-23 |
| Sources | 25 bibliography entries; 23 ledger source keys; 23 chapter source keys; only `AWS-MLLENS-2025` and `NIST-PLAYBOOKAUDIT-2023` are intentionally bibliography-only scope/provenance records |
| Coverage appendix | All 72 claim IDs appear; no missing or extra ID; coverage reaches `CH01-C072` and preserves multi-source synthesis mappings |
| Glossary | Nine externally sourced definitions and five explicit handbook syntheses; every external key resolves; Kubernetes and MLflow provenance/version limits are current |
| External URLs | 36/36 unique bibliography URLs returned HTTP 200 after redirects |
| Mandated claim-ID AWK | Exit 0; no output |
| Mandated P0/P1-status AWK | Exit 0; no output |
| Custom field, sequence, duplicate, deadline, ledger-key, chapter-key, and coverage checks | Exit 0; no findings |
| Validator test harness | Exit 0; all 27 tests passed |
| Release validator | Exit 0; zero `FAIL:` lines |
| Maintained unresolved-marker scan | No matches with `--glob '!**/scripts/**'` |
| Historical plan marker form | Script-only false positives: the `TODO` failure fixture and validator's literal `VERIFY` matcher, because `--glob '!scripts/**'` does not exclude the nested script tree |
| Generated-fence and banned-phrase policy | Release validator reports clean maintained content; banned-phrase scan has no match. The raw plan fence scan sees only validator script fixtures/implementation, not maintained Markdown. |

The evidence gate is approved with the one Minor source-metadata cleanup above.

## Changelog

### 2026-08-23

- Completed the focused evidence rereview after Task 8 evidence, technical, and editorial corrections.
- Closed prior I1-I5 and the maintained-content portion of prior M1; independently rechecked all 72 claims, 25 sources, 36 external URLs, glossary provenance, point-of-use synthesis boundaries, coverage, and fresh validators.
- Recorded one non-blocking Minor defect in the SLSA immutable-link label and approved the evidence rereview with zero Critical and zero Important findings.
