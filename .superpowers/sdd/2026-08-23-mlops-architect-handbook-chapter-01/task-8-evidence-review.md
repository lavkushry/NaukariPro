# Task 8 Independent Evidence Review

## Verdict

**REQUEST CHANGES — not approved.** The review found **0 Critical, 5 Important, and 1 Minor** findings. Chapter 1 must remain below `Verified` and `Publication Ready` until all Important findings are corrected and independently rereviewed.

The current ledgered Chapter 1 facts are otherwise strong: all 42 P0/P1 rows are `verified`; all nine architectural syntheses remain `qualified`; their repeated chapter uses preserve point-of-use boundaries; and the coverage appendix reconciles all 65 claim IDs. The blocking defects are stale false claims in the retained research evidence, incomplete version reproducibility, and security prescriptions in the chapter that bypass the mandatory claim-ledger contract.

## Review scope and method

The review read in full `AGENTS.md`, `CLAUDE.md`, the approved design, Task 8 brief, the ECC deep-research skill, all 519 lines of Chapter 1, all 65 claim-ledger rows, all 23 bibliography entries, all 14 controlled glossary terms, all three research reports, the Task 4 and Task 5 reviews and rereviews, `STYLE_GUIDE.md`, and `EDITORIAL_STATUS.md`.

Every Chapter 1 citation was reconciled against its ledger row, bibliography scope, claim type, risk, status, version/date fields, review deadline, and point-of-use evidence label. Primary-source checks used the canonical papers, official specifications, and first-party documentation. Live checks confirmed that all 28 unique bibliography URLs return HTTP 200. Representative volatile metadata was also rechecked: MLflow 3.15.1 was released on 2026-08-02; the pinned MLflow documentation is version 3.15.1; the current Kubernetes documentation identifies itself as v1.36; Team Topologies exposes `datePublished=2019-11-07` and `dateModified=2024-06-01`; and the NIST page still states on the review date that AI RMF 1.0 is under revision.

## Findings

### Critical

None.

### Important

#### I1. The foundations research report still makes the rejected causal claim about the 36 interviews

Evidence:

- `mlops/architect-handbook/sources/research/chapter-01-foundations.md:45` labels as a **Sourced fact** that the rubric “was derived from Google experience and structured interviews with maintainers of 36 systems.”
- The primary paper says the rubric was based on decades of Google production-ML engineering. Its application section then says Google teams were evaluated in structured interviews “based on the rubric detailed above”; the authors met 36 teams. The interviews applied or verified the already described rubric rather than co-deriving it. [Breck et al., 2017](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- This is the same semantic defect previously identified in `task-5-review.md` I1. It was corrected in `claim-ledger.csv:10` and Chapter 1 line 141, but not in the retained research report.

Impact: a maintained source report still presents a false quantitative/provenance statement as source-entailing, so the evidence package contradicts its corrected ledger and cannot support a release audit.

Required fix: replace the sentence with the corrected boundary already used by `CH01-C009`: the rubric was based on decades of Google production-ML engineering and was applied through structured interviews with 36 Google teams. Update the research-report changelog and recheck the full paragraph against the paper.

#### I2. The platform research report still over-attributes the API/documentation/tooling definition to Team Topologies and retains false date metadata

Evidence:

- `mlops/architect-handbook/sources/research/chapter-01-platform-strategy.md:75` labels as a **Sourced fact** that Team Topologies defines a thinnest viable platform as “the smallest set of APIs, documentation, and tools.”
- The cited page says a TVP should be no thicker than necessary and may be only a wiki page naming an approved cloud provider, approved services, and usage guidance. It does not define an API/documentation/tooling trio. [Team Topologies TVP guidance](https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp)
- `chapter-01-platform-strategy.md:53` says the year is unstated, while the page's first-party metadata exposes publication on 2019-11-07 and modification on 2024-06-01.
- This is the same source-scope defect previously fixed in `claim-ledger.csv:49` and `references.md:255-264`; the research report was not reconciled.

Impact: the maintained research report disagrees with the verified ledger and bibliography on both entailment and source metadata.

Required fix: use the bounded wording from `CH01-C048`; record both exposed dates; retain practitioner-guidance scope; and update the report changelog and any source-count/hash records that cover this file.

#### I3. The foundations report still cites moving `/latest/` pages as fixed MLflow 3.15.1 evidence

Evidence:

- `chapter-01-foundations.md:75` and `:77` label MLflow 3.15.1 behaviors as **Sourced fact** but link to `/docs/latest/`.
- Its own applicability note at `:100` admits those URLs are volatile, and its source register repeats them at `:123-124`.
- `references.md:79-99` correctly pins the same claims to `https://mlflow.org/docs/3.15.1/ml/tracking/` and `https://mlflow.org/docs/3.15.1/ml/model-registry/workflow/`. Live review confirmed both versioned pages entail `CH01-C018` through `CH01-C021` and the Model registry and Artifact store glossary definitions.
- This repeats Task 5 I3 inside a retained evidence artifact even though the bibliography was corrected.

Impact: a reader following the research report cannot reproduce the asserted 3.15.1 evidence after `/latest/` advances.

Required fix: replace all four moving links in the foundations report with the versioned 3.15.1 URLs, retain the 2026-08-02 release record, remove the now-resolved volatility warning or rewrite it as a normal review-deadline statement, and refresh the report changelog and recorded hash.

#### I4. Kubernetes product claims are called version-scoped without a Kubernetes release pin or immutable evidence URL

Evidence:

- `claim-ledger.csv:15-18` classifies `CH01-C014` through `CH01-C017` as P1 product behavior and says the claims are version-scoped, but `source_version` contains only a page-modification date.
- `references.md:46-77` labels the canonical moving documentation URLs as stable and likewise records only page modification dates, not the Kubernetes release. The same source boundary reaches Chapter 1 lines 18, 89, and 93 and the Control plane glossary definition at `GLOSSARY.md:11`.
- Live first-party pages identify the current documentation as Kubernetes v1.36. Their content entails the four claims today, but the canonical URLs will move with the documentation release and do not reproduce the reviewed snapshot.
- Immutable official source-file permalinks are available for the reviewed revisions: [components](https://github.com/kubernetes/website/blob/6e5065edcfd577d59c7c9ee18b238ecbc91675fe/content/en/docs/concepts/overview/components.md), [controllers](https://github.com/kubernetes/website/blob/7e64c2db8236a6b7325cf82ec050783a1b0a3850/content/en/docs/concepts/architecture/controller.md), and [workloads](https://github.com/kubernetes/website/blob/af5b13e33446de715819ed64e0d45085c70c1bf5/content/en/docs/concepts/workloads/_index.md).
- `STYLE_GUIDE.md:62` requires product behavior to be version-pinned; the design requires stable authoritative links and version-pinned product behavior.

Impact: the 90-day deadlines limit freshness risk but do not make the evidence snapshot reproducible or satisfy the separate version-pin requirement.

Required fix: record Kubernetes v1.36 in the three bibliography versions and four ledger rows; retain the human-readable canonical pages; add immutable first-party source permalinks for the reviewed revisions; and recheck `CH01-C014` through `CH01-C017` plus the Control plane glossary row against that snapshot.

#### I5. Chapter 1 contains security requirements and effectiveness claims that have no ledger row, source, or point-of-use synthesis boundary

Evidence:

- `STYLE_GUIDE.md:53-60` requires a ledger row for every security-related factual claim and a source/synthesis label at point of use. The approved design acceptance criterion requires supporting evidence for every security and normative claim.
- Chapter 1 line 95 says security “requires strong authentication, scoped authorization, tamper-evident decision records, and emergency access procedures.”
- Lines 101 and 107 state that encryption/access logging protect the path and that isolation, secret scoping, dependency integrity, and artifact signing reduce attack paths.
- Lines 199 and 211 say access controls, integrity checks, restore tests, signed artifacts, scoped deploy authority, and auditable emergency actions are required.
- Line 388 separately mandates integrity and access controls for source, build, data, artifact, and control records before the correctly qualified SLSA/NIST synthesis begins.
- None of those specific control requirements or effectiveness claims appears in `claim-ledger.csv`. The adjacent qualified rows `CH01-C056` through `CH01-C061` cover architecture boundaries; they do not evidence these control lists. The current NIST and SLSA citations should not be stretched to controls they do not individually entail.

Impact: the claim-coverage appendix is complete only for the preselected 65 rows, not for every security assertion actually published in the chapter. This directly violates the evidence contract despite the validator passing.

Required fix: inventory every security/normative sentence in Chapter 1. For externally asserted controls, add P0/P1 rows with exact authoritative evidence and point-of-use citations. For local architecture recommendations, use explicit `Handbook synthesis (bounded)` labels, stated assumptions, and qualified ledger rows. Narrow or remove any control whose source does not entail the wording. Rebuild the coverage appendix after the ledger changes.

### Minor

#### M1. The prescribed unresolved-marker scan is not clean even though the matches are not unresolved markers

The exact Task 8 scan returns `chapter-01-governance-reliability.md:38` because case-insensitive `VERIFY` also matches the ordinary verb “verify,” and it returns validator-script fixtures because `--glob '!scripts/**'` does not exclude the nested handbook script paths from this invocation. The release validator correctly reports no unresolved marker. This is a scan-contract false positive rather than an evidence defect.

Required fix: either reword the ordinary verb and use `--glob '!**/scripts/**'`, or document a case-sensitive marker scan that still catches the intended uppercase tokens. The Task 8 report should not claim that the prescribed command produced zero matches until the command/output contract is reconciled.

## Evidence audit conclusions

| Gate | Result |
| --- | --- |
| Claim-ledger structure | Pass: 65 sequential rows; 13 non-empty fields; unique IDs; no unresolved source keys |
| Risk/status counts | P0: 14; P1: 28; P2: 23; `verified`: 56; `qualified`: 9 |
| Existing high-risk status | Pass mechanically: all 42 P0/P1 rows are `verified`; no deadline is overdue on 2026-08-23 |
| Existing ledgered claim entailment | Pass except for reproducibility finding I4: the current primary pages entail the prose, and vendor/framework scope is preserved |
| Qualified synthesis boundaries | Pass: all nine qualified rows are bounded; repeated chapter uses retain point-of-use labels and exact source families |
| Quantitative claims | Pass: 28 checks and 36 teams are primary-source quantities in the corrected ledger/chapter; exercise targets are explicitly invented and illustrative; no production metric or comparative cost result is presented as fact |
| Bibliography/source class | 23 entries; source classes and vendor applicability boundaries are appropriate; all 28 unique external URLs returned HTTP 200 |
| Glossary provenance | Pass except inherited Kubernetes pinning in I4: nine externally sourced definitions and five explicit handbook syntheses are correctly distinguished |
| Coverage appendix | Pass for `CH01-C001` through `CH01-C065` and all 21 chapter citation keys; it must be regenerated if I5 adds rows |
| Research-report consistency | Fail: I1-I3 retain defects already corrected downstream |
| Unsupported assertions | Fail: specific security prescriptions in I5 are outside the ledger |

## Fresh verification

```text
Mandated claim-ID AWK: exit 0; no output
Mandated P0/P1-status AWK: exit 0; no output
Custom 13-field, unique-ID, deadline, ledger-source-key, chapter-source-key, and stale-key checks: exit 0; no structural findings
bash mlops/architect-handbook/scripts/test_validate_handbook.sh: exit 0; 27/27 tests passed
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile release mlops/architect-handbook: exit 0; zero FAIL lines
Live bibliography links: 28/28 unique URLs returned HTTP 200
Task 8 exact marker scan: non-zero matches described in M1
Generated-fence and banned-phrase scans: no maintained-content findings
```

Automated validation cannot detect the five semantic evidence defects above. The evidence review is therefore **not approved**.

## Re-review boundary

After correction, reread the changed paragraphs in both research reports, the Kubernetes bibliography and ledger rows, all changed security prose and new claim rows, affected glossary definitions, and the complete coverage appendix. Re-run live source checks, both mandated AWK commands, source-key reconciliation, the 27-test harness, and release validation. Approval requires zero Critical and zero Important findings.

## Changelog

### 2026-08-23

- Completed the independent Task 8 evidence audit of Chapter 1, the ledger, bibliography, glossary, three research reports, prior evidence reviews, source metadata, freshness rules, and live primary sources.
- Recorded five Important semantic/reproducibility/coverage findings, one Minor scan-contract finding, and fresh validator evidence.
