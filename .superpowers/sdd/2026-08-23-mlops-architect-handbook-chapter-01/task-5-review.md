# Task 5 Independent Review

## Verdict

**REQUEST CHANGES — not approved.** The audit found zero Critical findings; three Important findings; and zero Minor findings. Task 5 cannot be approved until every Important finding is fixed and the report; hashes; and review package are refreshed.

## Review scope

The review read the complete workspace instructions; design specification; Task 5 brief; implementation report; review-package diff; all three Task 4 research reports; all Task 4 review artifacts; bibliography; claim ledger; glossary; style guide; validator policy; validator implementation; and validator test harness. The live artifacts and the packaged diff were audited independently rather than relying on the implementation report.

| Artifact | Audited | Result |
| --- | ---: | --- |
| Bibliography entries | 23 of 23 | 20 pass; 3 entries are affected by Important findings 2 and 3 |
| Claim-ledger rows | 65 of 65 | All structural checks pass; 63 are exactly entailed; 2 are not |
| P0/P1 claims | 42 of 42 | All 14 P0 pass; 27 of 28 P1 pass exact entailment |
| Qualified P2 syntheses | 9 of 9 | All are explicitly qualified and preserve their limitations |
| Glossary definitions | 14 of 14 | All wording is accurate and bounded; 2 externally sourced rows inherit the MLflow stable-link defect |

## Findings

### Critical

None.

### Important

#### I1. `CH01-C009` reverses the relationship between rubric derivation and the 36 interviews

Evidence:

- `mlops/architect-handbook/sources/claim-ledger.csv:10` says the ML Test Score rubric "was derived from Google experience and structured interviews with maintainers of 36 systems" and marks that quantitative P1 claim `verified`.
- The cited paper first says the rubric is based on decades of production-ML engineering at Google. Its later evaluation section says the teams received a structured interview based on the rubric already detailed, and that the authors met 36 Google teams. The interviews evaluated or verified the rubric's advice; the source does not say they co-derived the rubric.
- Consequently, `task-5-report.md:67` is false when it says every P0/P1 row marked `verified` remains entailed by its source.

Impact: this is a high-risk quantitative row whose causal wording is not exactly entailed, violating Task 5 Step 2.

Required fix: separate provenance from evaluation. For example: "The ML Test Score rubric was based on decades of Google production-ML engineering experience and was evaluated through structured interviews with 36 Google teams." Recheck the precise `teams` versus `systems` context against the paper; update the note; and retain P1/`verified` only if the final wording is exactly supported. Refresh `task-5-report.md` and the review package.

Primary evidence: [The ML Test Score paper](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/).

#### I2. `CH01-C048` and `TEAMTOPOLOGIES-TVP-2026` attribute a synthesized API/documentation/tooling definition to Team Topologies

Evidence:

- `mlops/architect-handbook/sources/claim-ledger.csv:49` calls a thinnest viable platform "the smallest API documentation and tooling set" and marks the P2 row `verified` against only `TEAMTOPOLOGIES-TVP-2026`.
- The cited page says a thinnest viable platform should be no thicker than necessary; may be only a wiki page identifying an approved cloud provider; services; and usage guidance; and should treat stream-aligned teams as customers with attention to developer experience. It does not define the concept as an API/documentation/tooling trio.
- `mlops/architect-handbook/sources/references.md:259` says the year is unstated, although the page metadata records publication on 2019-11-07 and modification on 2024-06-01. Line 264 repeats the unsupported "API; documentation; and tooling boundary" as supported scope.
- `task-5-report.md:18` says cross-source architectural judgments remain P2 and `qualified`; this fused judgment is instead labeled `verified`.

Impact: both the verified-row entailment contract and one bibliography supported-scope/metadata contract are inaccurate.

Required fix: either rewrite `CH01-C048` to the page's actual bounded guidance and keep it attributed/verified, or cite the additional source that supports the API/documentation/tooling synthesis and mark the row `qualified`. Correct the bibliography date metadata and supported scope. If the key-year convention denotes source publication or update year, reconcile the key as well; otherwise document why the access-year key is stable. Refresh counts if status changes; hashes; report; and review package.

Primary evidence: [Team Topologies TVP guidance](https://teamtopologies.com/key-concepts-content/what-is-a-thinnest-viable-platform-tvp).

#### I3. Both MLflow bibliography records use moving `/latest/` documentation while claiming a fixed 3.15.1 evidence snapshot

Evidence:

- `mlops/architect-handbook/sources/references.md:85` points `MLFLOW-TRACKING-2026` to `https://mlflow.org/docs/latest/ml/tracking/`, while lines 83 and 86-88 claim MLflow 3.15.1 metadata; version; and behavior.
- `mlops/architect-handbook/sources/references.md:96` does the same for `MLFLOW-REGISTRY-2026`, while lines 94 and 97-99 claim MLflow 3.15.1.
- A release announcement establishes that 3.15.1 existed on the recorded date, but it does not freeze the behavioral content of a moving `/latest/` page. Versioned documentation is available at `https://mlflow.org/docs/3.15.1/ml/tracking/` and `https://mlflow.org/docs/3.15.1/ml/model-registry/workflow/`.
- The unstable evidence path supports P1 rows `CH01-C018` through `CH01-C021` at `claim-ledger.csv:19-22` and the Model registry and Artifact store definitions at `GLOSSARY.md:15-16`. It conflicts with `task-5-report.md:18` and `:80`, which claim product-version and stable-source-key boundaries.

Impact: the claims appear entailed by the currently served documentation, but the bibliography cannot reproduce the asserted 3.15.1 evidence after `/latest/` advances. This violates the required stable URL/version contract for volatile P1 product behavior.

Required fix: replace both `/latest/` links with the versioned 3.15.1 documentation URLs; retain the release record as release-date evidence; recheck `CH01-C018` through `CH01-C021` and the two glossary definitions against those snapshots; then refresh hashes; report; and review package.

### Minor

None.

## Row-by-row audit conclusions

### Bibliography

All 23 keys are unique; uppercase; resolve from their consumers; identify an appropriate source class; and contain all eight required fields. Twenty entries have adequate metadata and a supported scope bounded to the cited source. The two MLflow entries fail stable version pinning, and the Team Topologies entry has inaccurate date metadata and an overstated supported scope. Accessed dates are present for all entries. No other unsupported cross-vendor or cross-domain scope was found.

### Claim ledger

Every physical row has exactly 13 comma-delimited fields; every field is non-empty; and IDs are unique and sequential from `CH01-C001` through `CH01-C065`. Semicolons are used inside prose, so commas do not split the CSV or defeat the mandated AWK checks. Every source key resolves.

Claim types and risk levels are appropriately conservative. All 14 P0 rows and 27 of 28 P1 rows are exactly entailed; `CH01-C009` is the sole high-risk entailment failure. Of 23 P2 rows, all 9 architectural syntheses are visibly `qualified` with limitations in `notes`; 13 of 14 verified P2 rows are directly entailed; `CH01-C048` is the exception. No other invented metric; product behavior; security rule; or normative requirement was found.

All `source_version`; `source_date`; `accessed_date`; and `review_by` fields are populated. The review dates implement the required policy: product behavior is 90 days; security guidance is 180 days; and foundational or lower-volatility material is one year, with the NIST revision trigger preserved in the relevant notes/report. No 30-day pricing; quota; or advisory claim is present. The MLflow source-version values are internally consistent but not reproducibly linked until Important finding I3 is fixed.

### Glossary

All 14 definitions are accurate; scoped; and accompanied by notes. Nine definitions use resolving bibliography keys and five use the explicit `Handbook synthesis` state. The synthesis definitions are not presented as external standards. Acronym guidance is present. The Model registry and Artifact store wording is supported by current MLflow documentation, but their source keys inherit Important finding I3's moving-link defect.

### Report and review package

The live hashes match `task-5-report.md:125-127`, and the stored review-package diff is byte-consistent with a fresh diff from the preserved baseline. Counts in the report match the live artifacts. The report's semantic assurances at lines 18; 67; and 80 overstate the result because of I1-I3.

## Fresh verification

The following checks were run against the live workspace during this review:

```text
Mandated claim-ID AWK: exit 0; no output
Mandated P0/P1-status AWK: exit 0; no output
Custom 13-field; non-empty; enum; sequential-ID; deadline; and source-key audits: exit 0; no findings
bash mlops/architect-handbook/scripts/test_validate_handbook.sh: exit 0; all 27 tests passed
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook: exit 0; 11 checks passed
Fresh baseline-to-live diff versus task-5-review-package.diff: byte-identical
```

These mechanical passes do not detect the semantic entailment and stable-evidence defects above.

## Approval gate

Do not approve Task 5. Fix I1-I3; update affected metadata/rows/glossary references; regenerate `task-5-report.md` hashes and `task-5-review-package.diff`; rerun the mandated AWK checks; the complete 27-test suite; live structure validation; and a fresh semantic spot-check of every changed claim.

## Changelog

### 2026-08-23

- Completed the independent 23-entry bibliography; 65-row claim-ledger; and 14-definition glossary audit.
- Recorded three Important evidence-contract findings and fresh validator results.
