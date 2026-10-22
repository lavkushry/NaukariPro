# Task 8 Evidence Correction Report

## Outcome

Implemented the evidence-only correction pass for Task 8 findings I1-I5 and M1. The retained research reports now agree with the verified ledger on ML Test Score provenance; Team Topologies wording and metadata; MLflow 3.15.1 links; and Kubernetes v1.36 behavior. Chapter 1 security and normative prose now distinguishes externally verifiable control facts from bounded handbook recommendations. The claim ledger extends sequentially through `CH01-C072`.

This report does not grant technical or publication approval. Diagram and non-evidence technical findings remain outside this implementer's scope and require the assigned technical correction and independent rereview.

## Scope and process

Read in full the workspace instructions; design; Task 8 brief; evidence and technical review reports; Chapter 1; all 65 starting claim rows; bibliography; glossary; three research reports; style guide; ECC deep-research skill; and Superpowers verification-before-completion skill.

Edited only these evidence-related handbook files:

- `sources/research/chapter-01-foundations.md`
- `sources/research/chapter-01-platform-strategy.md`
- `sources/research/chapter-01-governance-reliability.md`
- `sources/references.md`
- `sources/claim-ledger.csv`
- `GLOSSARY.md`
- `chapters/01-mlops-architecture-foundations.md`
- `CHANGELOG.md`

Also created this execution report. No diagram; status; progress; validator script; test script; or `mlops/vol1.md` file was edited.

## Finding resolutions

| Finding | Resolution | Evidence boundary |
| --- | --- | --- |
| I1 | Replaced the rejected causal wording with the paper's sequence: decades of Google production-ML engineering informed the rubric; structured interviews applied it to 36 Google teams. | Breck et al. 2017 primary paper |
| I2 | Replaced the unsupported API/documentation/tool trio with the source-entailing TVP wording and recorded publication on 2019-11-07 plus modification on 2024-06-01. | Team Topologies first-party metadata and page |
| I3 | Replaced every moving MLflow behavior link in the foundations report with the 3.15.1 page and retained the 2026-08-02 release record. | MLflow 3.15.1 first-party docs and release record |
| I4 | Recorded Kubernetes v1.36 in all three bibliography entries and `CH01-C014` through `CH01-C017`; retained readable pages and added immutable official `kubernetes/website` revision permalinks. | Kubernetes first-party pages and exact official source revisions |
| I5 | Added four verified P0 facts and two qualified P2 security syntheses; bounded every published control recommendation by assumptions and local assessment; rebuilt point-of-use citations and the coverage appendix. | NIST SP 800-53 Rev. 5 Release 5.2.0; SLSA v1.2 Build and artifact-verification specification |
| Technical M1 | Replaced the statement that signing reduces attack paths. Signing is now paired with trusted provenance-envelope and subject-digest verification plus policy admission. | `CH01-C069` and qualified `CH01-C071` |
| Provider evidence foundation | Added qualified `CH01-C072` for explicit service-boundary; support; escalation; change; observability; audit; export; and exit allocations only where actual documentation and terms establish them. | Bounded AWS; Azure; and CNCF synthesis |
| Evidence M1 | Reworded the ordinary verb in the governance report that collided with the case-insensitive marker scan and recorded the change in that report's changelog. | No evidence meaning changed |

## Security and normative sentence inventory

Every Chapter 1 region containing security; safety; governance; access; integrity; signing; privacy; retention; third-party; incident; or normative control language was classified as sourced fact; bounded synthesis; illustrative requirement; or non-claim boundary.

| Chapter lines after correction | Classification and disposition | Ledger foundation |
| --- | --- | --- |
| 18-24 | Prerequisites and explicit assumptions; law and sector applicability remains outside scope. | Non-claim boundary |
| 30-48 | Scientific and AI-risk facts retain primary citations; unauthorized-substitution language is bounded by threat model; implementation; assessment; trusted verification; and admission policy. | `CH01-C001-C005`; `CH01-C037`; `CH01-C070-C071` |
| 69-81 | Continuing evaluation; approval separation; inventories; monitoring; incidents; third-party risk; and retirement remain exact NIST or Google facts plus bounded synthesis. | `CH01-C026-C027`; `CH01-C031-C032`; `CH01-C044`; `CH01-C059` |
| 93-101 | Control-plane authentication/access/logging/emergency paths and data-path cryptography/access/logging are explicitly tailored recommendations; no effectiveness guarantee remains. | `CH01-C066-C067`; qualified `CH01-C070` |
| 105-113 | Training and serving recommendations state risk assumptions; signing is coupled to trusted verification and policy admission; process isolation and least privilege are candidates rather than universal controls. | `CH01-C066-C069`; qualified `CH01-C070-C071` |
| 117-133 | Observability and AI RMF claims retain exact source scope; platform guardrails are visibly labeled as bounded contract design. | `CH01-C022-C024`; `CH01-C030`; qualified `CH01-C070` |
| 139-173 | Maturity remains an explicitly bounded model; manual/emergency access and isolated execution are scenario assumptions; NIST testing/response language remains sourced. | `CH01-C009-C010`; `CH01-C029`; `CH01-C043-C045`; qualified `CH01-C070-C071` |
| 179-219 | Record security recommendations now select access; logging; integrity; backup; recovery; artifact verification; and scoped identities according to classification and recovery objectives. | `CH01-C038-C041`; `CH01-C057`; `CH01-C060-C061`; `CH01-C066-C071` |
| 223-249 | The entire responsibility table remains bounded synthesis; the provider contract paragraph states assumptions and denies cross-provider universality or accountability transfer. | `CH01-C025`; `CH01-C032`; `CH01-C036`; `CH01-C042`; `CH01-C046-C051`; `CH01-C062`; `CH01-C072` |
| 251-298 | Vendor comparison factors retain vendor scope; third-party controls retain NIST scope; control review; portability; and exit are bounded decision recommendations. | `CH01-C042`; `CH01-C052-C055`; `CH01-C063`; `CH01-C072` |
| 300-329 | Security and governance statements sit inside the explicit bounded role model and now describe recorded interfaces; authorities; and escalation rather than universal controls. | Qualified `CH01-C064` |
| 334-358 | The nine-step reference flow is explicitly bounded synthesis; sourced stop/decommissioning facts and the reliability/risk separation retain citations. | `CH01-C028`; `CH01-C033-C036`; `CH01-C058-C060` |
| 362-392 | The fictional failure controls are explicitly labeled bounded; externally asserted monitoring and stop rules retain NIST citations; integrity and access recommendations are tailored; signing is coupled to verification/admission. | `CH01-C005`; `CH01-C013`; `CH01-C028-C029`; `CH01-C033`; `CH01-C037`; `CH01-C061`; `CH01-C066-C071` |
| 396-421 | Security; regions; retention; provider export; recovery; and responsibility requirements are declared invented exercise constraints. | Illustrative and bounded; not production facts |
| 423-466 | Questions and scoring criteria are handbook evaluation artifacts; level thresholds are explicitly illustrative and bounded rather than external hiring standards. | Non-factual exercise/rubric boundary |
| 468-485 | Sourced and qualified takeaways retain point-of-use labels; product and NIST version limits remain explicit. | `CH01-C058-C065` plus coverage below |

## New evidence rows

| Claim | Risk/status | Source and scope |
| --- | --- | --- |
| `CH01-C066` | P0 `verified` | NIST controls for account management; identification/authentication; access enforcement; and least privilege |
| `CH01-C067` | P0 `verified` | NIST controls for event logging; audit protection; cryptographic protection; and transmission/storage confidentiality |
| `CH01-C068` | P0 `verified` | NIST controls for information integrity; process isolation; backup; and recovery/reconstitution |
| `CH01-C069` | P0 `verified` | SLSA v1.2 verification of provenance signature; artifact subject digest; predicate type; and expectations |
| `CH01-C070` | P2 `qualified` | Tailored control selection for the bounded predictive workload; no universal baseline or effectiveness claim |
| `CH01-C071` | P2 `qualified` | Signing plus trusted provenance/digest verification and policy admission; SLSA Build scope retained |
| `CH01-C072` | P2 `qualified` | Provider operating-contract allocation only where documentation and actual terms establish each duty |

## Counts after correction

- Claims: 72 total.
- Risk: P0 18; P1 28; P2 26.
- Status: 60 `verified`; 12 `qualified`.
- High risk: all 46 P0/P1 rows are `verified`; no P0/P1 row is qualified.
- Bibliography: 25 entries and 36 unique external URLs.
- Chapter citation keys: 23; every chapter key resolves to the bibliography.
- Claim IDs: sequential and unique from `CH01-C001` through `CH01-C072`.
- CSV: exactly 13 comma-delimited non-empty fields on every row.

## Live primary-source checks

- All 36 unique bibliography URLs returned HTTP 200 on 2026-08-23.
- MLflow 3.15.1 tracking; registry; and release URLs returned HTTP 200.
- Kubernetes v1.36 readable pages and all three immutable official source revisions returned HTTP 200.
- The NIST publication page; DOI; and immutable official OSCAL catalog returned HTTP 200. The catalog identifies Release 5.2.0; the NIST page records its 2025-08-27 minor release.
- The SLSA v1.2 artifact-verification page and immutable official version-branch source returned HTTP 200 and state the signature; subject-digest; predicate-type; and expectation checks used by `CH01-C069`.
- The Breck paper; Team Topologies page; AWS; Azure; and CNCF sources returned HTTP 200.

## Verification evidence

- Mandated claim-ID AWK: exit 0; no output.
- Mandated P0/P1-status AWK: exit 0; no output.
- Sequential-ID; duplicate-ID; 13-field; non-empty-field; deadline; ledger-source-key; and chapter-source-key audits: exit 0; no findings.
- `bash mlops/architect-handbook/scripts/test_validate_handbook.sh`: 27/27 tests passed.
- Structure profile: initially exposed the marker collision in source key `SLSA-VERIFY-2026`; the key was renamed `SLSA-VERIFICATION-2026` without changing source scope.
- Release profile after the rename: exit 0; zero `FAIL:` lines.
- Final marker command with `--glob '!**/scripts/**'`: no matches.
- Maintained-content generated-fence; banned-phrase; placeholder; stale-foundations wording; and moving-MLflow-link scans: no findings. The unfiltered generated-fence scan still sees the validator's intentional negative-test fixture inside `scripts/`; no maintained content matches.

## Current SHA-256 records

| File | SHA-256 |
| --- | --- |
| `sources/research/chapter-01-foundations.md` | `c46c9abef953c07bd27cc358ba5b7e1de80a63ed175c29b0e24756b1e059f387` |
| `sources/research/chapter-01-platform-strategy.md` | `5aff3bc095e0771dcdfddc164aea2eb1fdcfcf53abc7a9d287ee39f9db41465c` |
| `sources/research/chapter-01-governance-reliability.md` | `85a42dae9fa3e0c241532b124fe932acf3fbdb670ce394f74b144cbfb7bf6e47` |
| `sources/references.md` | `0e9bdb7e351b61a182926585f79c94fcfcb4e6ebf911a35d7b9776d71bf48a7f` |
| `sources/claim-ledger.csv` | `af336600f2cc57aabcd3723ed61e6853a20a75fdff14fd78cbe989aa34554225` |
| `GLOSSARY.md` | `cab3b6365f6707885d95d26928ed912d7e80cb8ef56de20ae1bca5a031ccbd57` |
| `chapters/01-mlops-architecture-foundations.md` | `579166e4ec68bdbd573e444b38b83267d1c9364fb12c460d3857522c23c2cb29` |
| `CHANGELOG.md` | `7b8003fb3abd620e363a38b9e866549e809d6ecddd7dabc5b87d8603910cf18d` |

Raw-source observation only: `mlops/vol1.md` SHA-256 `8f8b723153f2cbcd07eed5484b475a39eee8678941ae49dac52f29b2975a489f`; 307906 lines; 3708572 bytes; mtime `2026-08-23T15:59:18+0530`. No command or patch targeted that file.

## Evidence rereview Minor M1 follow-up

The focused evidence rereview identified that the SLSA `releases/v1.2` Git branch was movable even though the bibliography described it as immutable. The bibliography now retains the official versioned page at <https://slsa.dev/spec/v1.2/verifying-artifacts> and pairs it with immutable official source revision <https://github.com/slsa-framework/slsa/blob/ae7fc76215004e8fae250c877eff8919bf048e3b/spec/verifying-artifacts.md?plain=1>. The Version field records revision `ae7fc76215004e8fae250c877eff8919bf048e3b`.

This correction supersedes the earlier report wording “immutable official version-branch source” and the earlier `sources/references.md` hash. Both corrected URLs returned HTTP 200. The source key remains `SLSA-VERIFICATION-2026`; every ledger and chapter consumer still resolves. The 27-test harness passed 27/27; release validation exited 0 with zero failures; and source-key reconciliation produced no missing keys.

Corrected `sources/references.md` SHA-256: `f398323afcfcf3b1f4968f914c5619c20931335d75a58b82035620cd1f139df8`.

## Changelog

### 2026-08-23

- Closed evidence rereview Minor M1 by replacing the movable SLSA release-branch link with an immutable commit revision; rechecked both URLs; reconciled consumers; reran 27 tests and release validation; and recorded the corrected bibliography hash.
- Recorded the Task 8 evidence corrections; sentence-level security inventory; new claim and source boundaries; live-link results; validation evidence; counts; and hashes.
