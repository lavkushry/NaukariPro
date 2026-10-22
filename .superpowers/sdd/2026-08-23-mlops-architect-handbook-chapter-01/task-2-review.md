# Task 2 Review: Validator and Fixture-Driven Tests

## Spec Compliance

PARTIAL. The implementation satisfies most of the explicit Task 2 brief: both profiles exist and default/rejection behavior is correctly dispatched (`mlops/architect-handbook/scripts/validate_handbook.sh:367-410`); structure runs the seven required checks and release adds claim/section checks (`mlops/architect-handbook/scripts/validate_handbook.sh:401-410`); the ledger header is compared exactly (`mlops/architect-handbook/scripts/validate_handbook.sh:265-276`); and release rejects every parsed Chapter 1 P0/P1 row whose status is anything other than exact `verified`, consistent with Ruling R3 (`mlops/architect-handbook/scripts/validate_handbook.sh:310-334`; `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/progress.md:50`).

The required ten named assertions are present and use isolated temporary fixtures (`mlops/architect-handbook/scripts/test_validate_handbook.sh:3-6,47-97,99-167`). The controller's clean rerun and the matching script checkpoints support the reported green state (`.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-2-report.md:15-44`). Both scripts use Bash 3.2-compatible constructs, and focused syntax parsing succeeded.

The task is not fully compliant because the release interface can return status 0 after validation failures, registered-diagram validation does not prove four distinct diagram files, CommonMark internal-link coverage is incomplete, and the approved design's heading/placeholder/language checks are absent. These gaps conflict with the non-zero failure contract and validation design (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:120-121,192-196`; `docs/superpowers/specs/2026-08-23-mlops-architect-handbook-chapter-01-design.md:179-193`).

## Strengths

- Fixture writes are rooted under one `mktemp -d` directory and removed by a quoted trap; `make_valid_fixture` consistently writes through its supplied fixture root rather than the real handbook (`mlops/architect-handbook/scripts/test_validate_handbook.sh:3-6,35-97`).
- Ordinary failures accumulate in the parent shell because the implementation uses here-doc-fed loops instead of pipeline subshells; each check records all matches before final reporting (`mlops/architect-handbook/scripts/validate_handbook.sh:12-15,145-222,224-263,401-419`).
- Marker scanning excludes the validator's `scripts/` subtree while reporting file and line for content matches, as required (`mlops/architect-handbook/scripts/validate_handbook.sh:202-220`).
- Relative paths are resolved from the containing Markdown document, with query/fragment removal and ATX-anchor checking for the supported inline-link form (`mlops/architect-handbook/scripts/validate_handbook.sh:224-263`).
- The CSV reader handles quoted commas and doubled quotes, derives column positions from the header, and enforces the exact `verified` P0/P1 release semantics rather than accepting `qualified` (`mlops/architect-handbook/scripts/validate_handbook.sh:284-334`).
- The validator contains no file-writing operation; all redirections and fixture mutations are confined to the test harness's temporary tree (`mlops/architect-handbook/scripts/validate_handbook.sh:1-419`; `mlops/architect-handbook/scripts/test_validate_handbook.sh:35-97`).

## Issues by Critical/Important/Minor

### Critical

None.

### Important

1. **A run with exactly 256 accumulated defects exits successfully.** `fail` increments an unbounded integer, but the final command is `exit "$FAILURES"`; shell exit statuses are reduced modulo 256, so `exit 256` becomes status 0 (`mlops/architect-handbook/scripts/validate_handbook.sh:12-15,413-419`). This directly violates the interface requirement that status 0 occur only when the selected profile passes (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:120-121,196`). Keep the complete count in output, but clamp the process status to a non-zero value in the 1-255 range whenever `FAILURES > 0`.

2. **The release diagram gate can pass without four distinct diagram files.** `check_registered_diagrams` increments its count for every relative link and only checks whether each resolved target is a regular file; it neither deduplicates targets nor establishes that targets are diagram artifacts within the Chapter 1 diagram directory (`mlops/architect-handbook/scripts/validate_handbook.sh:87-110`). Four duplicate links to one `.mmd`, or four links such as `../../README.md`, satisfy this gate, contrary to the release requirement for all four registered diagram files and Ruling R4 (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:187`; `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/progress.md:51`). Validate four unique registry entries and constrain their resolved files to the approved Chapter 1 diagram registry contract.

3. **Internal-link validation covers only a subset of CommonMark links and anchors.** The extractor recognizes only inline `](...)` destinations, so a broken reference-style link such as `[Guide][guide]` plus `[guide]: missing.md` is never inspected (`mlops/architect-handbook/scripts/validate_handbook.sh:36-55`). The anchor generator also assigns no duplicate-heading suffixes, so a valid link to a repeated heading's generated anchor can be rejected (`mlops/architect-handbook/scripts/validate_handbook.sh:57-78`). This falls short of the CommonMark-compatible-link constraint and the design requirement for resolvable internal links/glossary anchors (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:24,192`; `docs/superpowers/specs/2026-08-23-mlops-architect-handbook-chapter-01-design.md:183-187`).

4. **Several checks assigned to `validate_handbook.sh` by the approved design are not implemented.** The dispatcher runs required-file, changelog, fence, generated-ID, marker, relative-link, ledger, and release-claim/section checks only (`mlops/architect-handbook/scripts/validate_handbook.sh:401-410`). There is no heading-hierarchy validation, no general placeholder-text validation beyond the four marker tokens, and no banned-generic-phrase or unsupported-superlative validation, although the approved validation design explicitly requires all three (`docs/superpowers/specs/2026-08-23-mlops-architect-handbook-chapter-01-design.md:181-191`). The Task 2 brief narrowed the function table, but it did not supersede the approved design; either implement these deterministic gates now or record an explicit ruling and assigned follow-up task before treating the release validator as complete.

### Minor

1. **The fixture suite proves the ten named examples but not several important branches of their contracts.** The link test covers only one missing inline file and no query, cross-document anchor, reference-style destination, or duplicate heading (`mlops/architect-handbook/scripts/test_validate_handbook.sh:130-134`). The claim test covers only one P1 `unverified` row, not P0 or the R3-significant `qualified`/`removed` statuses (`mlops/architect-handbook/scripts/test_validate_handbook.sh:142-149`). No negative test covers a missing/duplicate diagram, multiple accumulated defects, the 256-status boundary, or marker exclusion under `scripts/` (`mlops/architect-handbook/scripts/test_validate_handbook.sh:99-160`). Adding focused cases would make the suite guard the release semantics that the current happy-path fixture leaves unproven.

## Assessment

REQUEST CHANGES. The validator is cleanly structured, Bash 3.2-compatible, read-only, and passes the required ten fixtures and the real scaffold in structure mode. However, the zero-status wraparound is a direct release-safety defect, and the diagram/link gates permit false results. The missing design-mandated checks also prevent this script from serving as the complete publication release validator described by the approved design. Address the Important findings and add focused regression coverage before approving Task 2.

## Changelog

### August 23, 2026

- Reviewed Task 2 against the brief, approved design, global constraints, Rulings R2-R5, implementation report, and complete filesystem diff package.
- Recorded four Important findings and one Minor test-coverage finding; no Critical findings.
