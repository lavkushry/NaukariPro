# Task 2 Report: Build the Validator with Fixture-Driven Tests

## Status

- Status: DONE_WITH_CONCERNS
- Commits: none (non-git workspace)

## Delivered

- Created executable `mlops/architect-handbook/scripts/test_validate_handbook.sh` with isolated `mktemp -d` fixtures, trap-based cleanup, the required helper signatures, and ten named behavior assertions.
- Created executable `mlops/architect-handbook/scripts/validate_handbook.sh` with Bash 3.2-compatible `structure` and `release` profiles.
- Kept structure validation compatible with the current scaffold; release additionally requires Chapter 1, four registered diagrams, all fifteen approved H2 sections, and `verified` status for every Chapter 1 P0/P1 claim.
- Implemented accumulated, human-readable failures without modifying the validated handbook.

## TDD and verification evidence

- RED: the first harness run exited 1 because `validate_handbook.sh` was absent; the first assertion named the missing validator.
- GREEN: all ten named assertions passed and the harness exited 0.
- Real scaffold: structure validation exited 0 with eight `PASS:` lines and no `FAIL:` lines.
- Portability: both scripts parsed under `/bin/bash` 3.2.57, and ShellCheck returned zero findings.
- Extra read-only audits confirmed cross-document anchor validation, unknown-profile rejection, and release as the default profile.

## Test summary

```text
PASS: complete minimal fixture passes structure
PASS: missing required file is named
PASS: unbalanced fence names affected file
PASS: generated fence identifier fails
PASS: unresolved marker fails
PASS: broken relative link names target
PASS: malformed ledger header fails
PASS: unverified P0 or P1 Chapter 1 claim fails release
PASS: maintained Markdown requires changelog
PASS: complete release fixture passes release
PASS: all 10 validator tests passed
```

## Script checkpoints

| File | SHA-256 |
|---|---|
| `mlops/architect-handbook/scripts/validate_handbook.sh` | `a8038d116f6f86a2a22e2b6122b0f52ce760da62524a2e20f4a71c4afad0dff9` |
| `mlops/architect-handbook/scripts/test_validate_handbook.sh` | `b9fc9b7d098e3c4141ee96529dc3c6ce4c30ba2dae894cb0cd00489a9806add7` |

## Raw-source preservation

| Event | SHA-256 | Lines | Bytes | Modification time |
|---|---|---:|---:|---|
| Task start | ad726d53f325797e92e87e40ca966d349da6d586d71d0de3e256141e75262cde | 173052 | 2039271 | 2026-08-23T12:49:21+0530 |
| Task end | 09e381fb31fac073f327da308818a05044aa4c9ec6ea43b2d5f3f699617eb34b | 188834 | 2234664 | 2026-08-23T13:05:57+0530 |

No Task 2 operation targeted `mlops/vol1.md`. Its observed growth was external and was preserved without rollback.

## Concern

`mlops/vol1.md` grew concurrently by 15,782 lines and 195,393 bytes during Task 2. This is allowed by the plan, but downstream tasks must use the latest recorded state and must continue treating the raw manuscript as read-only.

## Fix Round 1

### Status and findings resolved

- Status: PASS_WITH_OBSERVED_EXTERNAL_GROWTH
- Clamped every accumulated failure count above 255 to process status 255 while retaining the complete count in human-readable output.
- Replaced link-count diagram validation with exact validation of the four approved, unique Chapter 1 files: `ml-lifecycle.mmd`, `architecture-planes.mmd`, `system-of-record.mmd`, and `failure-flow.mmd`.
- Added CommonMark reference-definition destinations, query/fragment stripping, cross-document anchor checks, and GitHub-style duplicate-heading suffix generation.
- Added deterministic gates for ATX heading hierarchy, placeholder text, banned generic phrases, and the spec's unqualified `best`, `always`, `never`, `guaranteed`, `latest`, and `currently` terms; prose checks exclude `scripts/` and fenced examples.

### Changed files

- `mlops/architect-handbook/scripts/validate_handbook.sh`
- `mlops/architect-handbook/scripts/test_validate_handbook.sh`
- `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-2-report.md`

### Focused RED evidence

Command: `/bin/bash mlops/architect-handbook/scripts/test_validate_handbook.sh`

The pre-fix run exited 1. All original ten assertions passed, while the nine new regressions reported these failures:

```text
FAIL: 256 accumulated defects retain a non-zero exit - command unexpectedly passed
FAIL: duplicate diagram targets fail release - command unexpectedly passed
FAIL: unapproved diagram targets fail release - command unexpectedly passed
FAIL: broken reference-style link names target - command unexpectedly passed
FAIL: duplicate heading suffix anchor resolves
FAIL: invalid heading hierarchy fails - command unexpectedly passed
FAIL: placeholder phrase fails - command unexpectedly passed
FAIL: banned generic phrase fails - command unexpectedly passed
FAIL: unqualified superlative fails - command unexpectedly passed
FAIL: 9 validator test(s) failed
```

### Verification commands and output

Commands:

```bash
/bin/bash -n mlops/architect-handbook/scripts/validate_handbook.sh
/bin/bash -n mlops/architect-handbook/scripts/test_validate_handbook.sh
shellcheck -s bash mlops/architect-handbook/scripts/validate_handbook.sh mlops/architect-handbook/scripts/test_validate_handbook.sh
/bin/bash mlops/architect-handbook/scripts/test_validate_handbook.sh
/bin/bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

The two syntax checks and ShellCheck exited 0 with no output. The full fixture harness exited 0:

```text
PASS: complete minimal fixture passes structure
PASS: missing required file is named
PASS: unbalanced fence names affected file
PASS: generated fence identifier fails
PASS: unresolved marker fails
PASS: broken relative link names target
PASS: malformed ledger header fails
PASS: unverified P0 or P1 Chapter 1 claim fails release
PASS: maintained Markdown requires changelog
PASS: complete release fixture passes release
PASS: 256 accumulated defects retain a non-zero exit
PASS: duplicate diagram targets fail release
PASS: unapproved diagram targets fail release
PASS: broken reference-style link names target
PASS: duplicate heading suffix anchor resolves
PASS: invalid heading hierarchy fails
PASS: placeholder phrase fails
PASS: banned generic phrase fails
PASS: unqualified superlative fails
PASS: all 19 validator tests passed
```

The real scaffold structure check exited 0:

```text
PASS: required files are present for structure profile
PASS: all maintained Markdown files contain ## Changelog
PASS: all Markdown fences are balanced
PASS: all maintained Markdown heading hierarchies are valid
PASS: no generated fence identifiers found
PASS: no unresolved marker tokens found
PASS: no unresolved placeholder text found
PASS: no banned generic phrases found
PASS: no unsupported superlatives found
PASS: all relative Markdown links resolve
PASS: claim-ledger.csv header matches the required schema
PASS: structure validation completed with zero failures
```

### Fix Round 1 checkpoints

| File | SHA-256 |
|---|---|
| `mlops/architect-handbook/scripts/validate_handbook.sh` | `0310dc1a2d42eb776e2c7cbc280d5a67013c81a9a9efe90b80ecce637c7a4a88` |
| `mlops/architect-handbook/scripts/test_validate_handbook.sh` | `16b2761c352932f7702506dda0e4033596f3e3698b79360c2f012660b3f9182d` |

The raw manuscript remained untouched by Fix Round 1. Its observed state advanced externally from the prior Task 2 checkpoint to SHA-256 `1662d7466835b2db4b8e6348fd816e6c69ea260b1b930821b9a02b60128f34d5`, 203,762 lines, 2,420,505 bytes, and modification time `2026-08-23T13:16:21+0530`.

## Fix Round 2

### Status and findings resolved

- Status: PASS
- Updated the release diagram contract to require exactly once each of `fig-01-ml-lifecycle.mmd`, `fig-02-architecture-planes.mmd`, `fig-03-systems-of-record.mmd`, and `fig-04-failure-propagation.mmd` inside `diagrams/chapter-01/`.
- Limited the diagram allowlist to `.mmd` registry targets; other relative navigation links are ignored by the diagram gate and remain enforced by general relative-link validation.
- Added one shared CommonMark fence-state filter for backtick and tilde fences of length three or greater, including matching-character and minimum-closing-length behavior. Link extraction, ATX-anchor slugging, heading hierarchy, placeholder, generic-phrase, and superlative scans consume only rendered lines outside fences.
- Restricted placeholder failures to deterministic unresolved forms such as `[PLACEHOLDER]`, `<PLACEHOLDER>`, underscored tokens, whole-line fill-in states, and explicit fill-in instructions. Legitimate policy prose containing the word `placeholder` passes.

### Changed files

- `mlops/architect-handbook/scripts/validate_handbook.sh`
- `mlops/architect-handbook/scripts/test_validate_handbook.sh`
- `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-2-report.md`

### Focused RED evidence

Command: `/bin/bash mlops/architect-handbook/scripts/test_validate_handbook.sh`

The round-2 pre-fix run exited 1. It showed the approved Task 6 targets and a valid non-`.mmd` navigation link being rejected, then reproduced every fence and placeholder false result:

```text
FAIL: complete release fixture passes release
FAIL: unapproved diagram target in diagrams/chapter-01/README.md:3: fig-01-ml-lifecycle.mmd
FAIL: unapproved diagram target in diagrams/chapter-01/README.md:7: ../../chapters/01-mlops-architecture-foundations.md#architecture-planes
FAIL: unbalanced tilde fence names affected file - command unexpectedly passed
FAIL: reference definitions inside fences are ignored
FAIL: broken relative link in README.md:12: missing-backtick.md
FAIL: broken relative link in README.md:16: missing-tilde.md
FAIL: ATX heading inside fence does not create anchor - command unexpectedly passed
FAIL: fenced ATX heading does not shift duplicate suffixes - command unexpectedly passed
FAIL: placeholder policy prose passes
FAIL: placeholder text in README.md:11:Placeholder text is forbidden in publication content.
FAIL: 7 validator test(s) failed
```

### Verification commands and output

Commands:

```bash
/bin/bash -n mlops/architect-handbook/scripts/validate_handbook.sh
/bin/bash -n mlops/architect-handbook/scripts/test_validate_handbook.sh
shellcheck -s bash mlops/architect-handbook/scripts/validate_handbook.sh mlops/architect-handbook/scripts/test_validate_handbook.sh
/bin/bash mlops/architect-handbook/scripts/test_validate_handbook.sh
/bin/bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Both Bash 3.2 syntax checks and ShellCheck exited 0 with no output. The full fixture harness exited 0:

```text
PASS: complete minimal fixture passes structure
PASS: missing required file is named
PASS: unbalanced fence names affected file
PASS: generated fence identifier fails
PASS: unresolved marker fails
PASS: broken relative link names target
PASS: malformed ledger header fails
PASS: unverified P0 or P1 Chapter 1 claim fails release
PASS: maintained Markdown requires changelog
PASS: complete release fixture passes release
PASS: 256 accumulated defects retain a non-zero exit
PASS: duplicate diagram targets fail release
PASS: unapproved diagram targets fail release
PASS: broken reference-style link names target
PASS: duplicate heading suffix anchor resolves
PASS: invalid heading hierarchy fails
PASS: placeholder phrase fails
PASS: banned generic phrase fails
PASS: unqualified superlative fails
PASS: unbalanced tilde fence names affected file
PASS: reference definitions inside fences are ignored
PASS: ATX heading inside fence does not create anchor
PASS: fenced ATX heading does not shift duplicate suffixes
PASS: placeholder policy prose passes
PASS: all 24 validator tests passed
```

The real scaffold structure check exited 0:

```text
PASS: required files are present for structure profile
PASS: all maintained Markdown files contain ## Changelog
PASS: all Markdown fences are balanced
PASS: all maintained Markdown heading hierarchies are valid
PASS: no generated fence identifiers found
PASS: no unresolved marker tokens found
PASS: no unresolved placeholder text found
PASS: no banned generic phrases found
PASS: no unsupported superlatives found
PASS: all relative Markdown links resolve
PASS: claim-ledger.csv header matches the required schema
PASS: structure validation completed with zero failures
```

### Fix Round 2 checkpoints

| File | SHA-256 |
|---|---|
| `mlops/architect-handbook/scripts/validate_handbook.sh` | `2c0cacfcd8f78c54bb42f3a914c845047d7193fbf2831ddf5190a8b651deb7e4` |
| `mlops/architect-handbook/scripts/test_validate_handbook.sh` | `8ae40f9e24cfa9f65f0f55985ac2b6d6713a1dbe50273cb12c10ba543d1fb374` |

`mlops/vol1.md` remained untouched and unchanged from the Fix Round 1 checkpoint: SHA-256 `1662d7466835b2db4b8e6348fd816e6c69ea260b1b930821b9a02b60128f34d5`, 203,762 lines, 2,420,505 bytes, modification time `2026-08-23T13:16:21+0530`.

## Changelog

### 2026-08-23

- Resolved all three Important findings from review round 2 and expanded the fixture harness from nineteen to twenty-four named cases.
- Resolved all four Important findings from review round 1 and expanded the fixture harness from ten to nineteen named cases.
- Completed the fixture-driven validator, RED/GREEN verification, real-scaffold validation, integrity checkpoint, and execution-ledger update.
