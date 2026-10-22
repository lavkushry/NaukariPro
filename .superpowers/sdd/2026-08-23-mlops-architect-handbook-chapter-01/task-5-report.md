# Task 5 Evidence Ledger and Bibliography Report

## Outcome boundary

Task 5 produced the Chapter 1 evidence set consumed by drafting. It does not approve chapter prose; diagrams; technical review; editorial review; release validation; or publication readiness.

## Implemented artifacts

- `mlops/architect-handbook/sources/references.md` now contains 23 authoritative bibliography entries with stable uppercase keys in `ORG-SHORTTITLE-YEAR` form.
- `mlops/architect-handbook/sources/claim-ledger.csv` now contains 65 unique pre-draft claims with exactly 13 comma-delimited fields per row.
- `mlops/architect-handbook/GLOSSARY.md` now contains 14 defined controlled terms. Nine definitions have source-entailing bibliography keys and five are explicit `Handbook synthesis` definitions.
- This execution report records the evidence boundaries; counts; hashes; and fresh validation results.

The preserved Task 5 baseline differs from the live handbook at exactly the three authorized handbook paths above. The report is the fourth Task 5 file created outside the handbook tree.

## Evidence synthesis method

The three approved Task 4 research reports were reconciled into one source namespace. Shared sources were deduplicated. Vendor documentation was retained only for that vendor's behavior or stated design position. Security and normative claims use NIST or SLSA sources. Product claims are version-scoped. Cross-source architectural judgments remain P2 and `qualified` rather than being presented as externally verified facts.

The ECC deep-research rules shaped source priority; claim-to-source entailment; fact-versus-synthesis separation; and explicit evidence gaps. The ECC article-writing rules kept definitions and claim text concrete and bounded. The Superpowers verification-before-completion gate required fresh checks after the final evidence edits.

## Independent-review finding reconciliation

| Finding | Correction | Evidence state |
| --- | --- | --- |
| I1 — ML Test Score provenance and interviews | `CH01-C009` now states that the rubric was based on decades of Google production-ML engineering and was later applied through structured interviews with 36 Google teams. The note explicitly separates provenance from application. | P1 and `verified`; the paper directly supports both clauses. |
| I2 — Team Topologies TVP scope and dates | `CH01-C048` now follows the page's bounded advice to keep the platform no thicker than necessary and its wiki-page example. The source key is `TEAMTOPOLOGIES-TVP-2019`; metadata records publication on 2019-11-07 and modification on 2024-06-01. | P2 and `verified`; no API; documentation; and tooling trio is attributed to this source. |
| I3 — MLflow reproducibility | The tracking and registry records now use versioned 3.15.1 documentation URLs. `CH01-C018` through `CH01-C021` and the Model registry and Artifact store definitions were rechecked against those pinned pages. | All four product rows remain P1 and `verified`; both glossary definitions remain `Verified`. |

## Bibliography result

- Entries: 23
- Required metadata fields per entry: title; author or organization; publication or update date; accessed date; stable URL or DOI; version; source class; and supported scope
- Access date: 2026-08-23 for every admitted source
- Resolution audit: every ledger key and every externally sourced glossary key resolves to one bibliography entry
- Scope controls: status-only NIST sources; SLSA Build boundaries; vendor applicability; pinned MLflow documentation; and product volatility are explicit

## Claim counts

### By claim type

| Claim type | Count |
| --- | ---: |
| Architectural synthesis | 9 |
| Normative or regulatory | 7 |
| Opinion or heuristic | 14 |
| Product or version behavior | 16 |
| Quantitative | 4 |
| Scientific or algorithmic | 7 |
| Security or safety | 8 |
| **Total** | **65** |

### By risk

| Risk | Count | Status distribution |
| --- | ---: | --- |
| P0 | 14 | 14 verified |
| P1 | 28 | 28 verified |
| P2 | 23 | 14 verified; 9 qualified |
| **Total** | **65** | **56 verified; 9 qualified** |

### Claim type by risk

| Claim type | P0 | P1 | P2 | Total |
| --- | ---: | ---: | ---: | ---: |
| Architectural synthesis | 0 | 0 | 9 | 9 |
| Normative or regulatory | 6 | 1 | 0 | 7 |
| Opinion or heuristic | 0 | 0 | 14 | 14 |
| Product or version behavior | 0 | 16 | 0 | 16 |
| Quantitative | 0 | 4 | 0 | 4 |
| Scientific or algorithmic | 0 | 7 | 0 | 7 |
| Security or safety | 8 | 0 | 0 | 8 |
| **Total** | **14** | **28** | **23** | **65** |

No P0 or P1 claim uses `qualified` or `removed`. Wording and notes carry the required scope so every high-risk row marked `verified` remains entailed by its cited source. The nine `qualified` rows are architectural synthesis and all are P2.

## Freshness policy

- Product or version behavior: review by 2026-11-21; 90 days after access.
- Security or safety guidance: review by 2027-02-19; 180 days after access.
- Foundational standards; canonical papers; and lower-volatility practitioner guidance: review by 2027-08-23; one year after access.
- NIST revision-sensitive rows also require review when NIST releases a revision if that occurs before the recorded date.

A dedicated audit confirmed that every claim has a non-empty `review_by` field and no claim exceeds its applicable policy deadline.

## Glossary result

All 14 controlled terms now have definitions. Externally entailed definitions use stable source keys. Data plane; training plane; serving plane; reproducibility; and architecture decision record were assessed individually; five entries remain explicit handbook synthesis. Acronym-bearing terms expand machine learning; machine learning operations; continuous training; service-level indicator; service-level objective; and architecture decision record at first use.

## Verification evidence

The following two required AWK commands were run verbatim after the final ledger edit. Both exited 0 with no output:

```bash
awk -F, 'NR==1 {next} $1 !~ /^CH01-C[0-9][0-9][0-9]$/ {print "bad claim id at row " NR; bad=1} END {exit bad}' mlops/architect-handbook/sources/claim-ledger.csv
awk -F, 'NR==1 {next} ($6=="P0" || $6=="P1") && $11!="verified" {print "unverified high-risk claim " $1; bad=1} END {exit bad}' mlops/architect-handbook/sources/claim-ledger.csv
```

Additional CSV audits exited 0 with no findings:

- Every row has exactly 13 comma-delimited fields.
- Every field is non-empty.
- Every claim ID is unique.

Full validator suite:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Result: exit 0; all 27 validator tests passed.

Live structure validation:

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Result: exit 0; all eleven check-level assertions passed and structure validation completed with zero failures.

Evidence-integrity audit:

- 23 bibliography entries each contain all eight required metadata fields.
- All ledger and glossary source keys resolve.
- All 14 glossary rows use an allowed stable key or `Handbook synthesis` state.
- All 65 claims have policy-bounded review dates.

These are Task 5 evidence and structure results. The release profile was not run because Chapter 1 and its diagrams belong to later tasks.

## Final hashes

```text
ca0f5de77dbf525ca7985df1fcea7cf84aca8a1d41f740bd21e92a5f488fd3c9  mlops/architect-handbook/sources/references.md
d528e45f7704427d9be611fce4863a07818c562834a079027b118a304f84d13d  mlops/architect-handbook/sources/claim-ledger.csv
0ea8fb278134043366e030171d196ee6a4cc80ec7cb7bc55a9e0d3208fa066b3  mlops/architect-handbook/GLOSSARY.md
```

## Raw-source observation

`mlops/vol1.md` was outside the write scope and no Task 5 edit targeted it. It grew externally during the final verification window and was not altered or rolled back by this task.

| Observation | SHA-256 | Lines | Bytes | Modification time |
| --- | --- | ---: | ---: | --- |
| Window start | `55e344ba301ec324fbfec68b483c00d7d101e62dd0b106af0121fdf285afe4a7` | 291251 | 3510135 | `2026-08-23T14:54:15+0530` |
| Window end | `a496be11616aeff7f8527a8d9b6f3188883c708335fe03cc746d10373028cb6e` | 300046 | 3612161 | `2026-08-23T15:00:15+0530` |

Observed growth was 8795 lines and 102026 bytes. The task made no unchanged-file assertion and took no corrective action against the live raw manuscript.

## Files changed

- `mlops/architect-handbook/sources/references.md`
- `mlops/architect-handbook/sources/claim-ledger.csv`
- `mlops/architect-handbook/GLOSSARY.md`
- `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-5-report.md`

## Changelog

### 2026-08-23

- Reconciled all three Important independent-review findings; corrected two claim entailment boundaries; pinned MLflow 3.15.1 evidence; corrected Team Topologies metadata and key year; and refreshed final hashes.
- Recorded the completed Task 5 bibliography; evidence ledger; glossary definitions; claim counts; freshness deadlines; file hashes; and verification evidence.
