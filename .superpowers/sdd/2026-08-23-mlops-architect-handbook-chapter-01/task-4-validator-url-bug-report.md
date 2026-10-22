# Task 4 Validator URL False-Positive Bug Report

## Outcome

The validator now excludes HTTP(S) Markdown destination URLs from the unsupported-superlative scan while continuing to reject `latest` in ordinary prose and non-URL inline code. The completed audit expanded the interrupted worker's 26-case harness to 27 cases because its original broad inline-code removal could hide non-URL prose.

No original RED run from the interrupted worker was observed or is claimed here. The URL regression was instead proved by a controlled temporary mutant that removed only the production URL sanitizers. A separate RED/GREEN cycle was observed for the audit-discovered inline-code boundary.

## Root Cause

`check_unsupported_superlatives` previously lowercased each unfenced Markdown line and applied the banned-token expression directly to the complete line. It did not distinguish visible prose from Markdown destinations. Therefore, a path segment such as `/latest/` inside an HTTP(S) destination was scanned as prose.

The preserved pre-fix validator reproduced the defect consistently against the live handbook:

```bash
bash .superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-4-before/handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Result: exit `5`. The validator reported five unsupported-superlative failures: one backticked `/latest/` URL-path fragment in `sources/research/chapter-01-foundations.md:100` and four AWS documentation destination URLs in `sources/research/chapter-01-platform-strategy.md:46-49`.

The interrupted implementation added three substitutions before the banned-token expression: remove all inline code, remove HTTP(S) autolinks, and remove bare HTTP(S) URLs. Comparison with the preserved Task 4 baseline showed that removing every inline-code span was not required by the defect and would suppress non-URL content such as `` `latest` ``.

## Regression Evidence

### Audit Boundary RED

The audit first added `latest in non-URL inline code fails` to the real harness without changing production code, then ran:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Result: exit `1`. Relevant output:

```text
PASS: latest inside an autolink destination passes
PASS: latest in ordinary prose fails
FAIL: latest in non-URL inline code fails - command unexpectedly passed
FAIL: 1 validator test(s) failed
```

This was the expected failure: the interrupted implementation's broad `` gsub(/`[^`]*`/, "", scan) `` removed the banned word before it could be evaluated.

### Audit Boundary GREEN

The broad inline-code substitution was narrowed to slash-delimited, backticked URL-path fragments. This preserves the live handbook's literal `` `/latest/` `` path reference without ignoring arbitrary inline-code prose.

The same full-suite command then exited `0`; all assertions passed, including:

```text
PASS: unqualified superlative fails
PASS: latest inside an autolink destination passes
PASS: latest in ordinary prose fails
PASS: latest in non-URL inline code fails
PASS: all 27 validator tests passed
```

### Controlled URL-Sanitization Mutant

A temporary directory was created with `mktemp -d /private/tmp/task4-validator-mutant.XXXXXX`. The final two scripts were copied into it, and only these two production lines were removed from the temporary validator:

```awk
gsub(/<https?:\/\/[^>]*>/, "", scan)
gsub(/https?:\/\/[^[:space:]>)]+/, "", scan)
```

The mutant harness was run with:

```bash
bash /private/tmp/task4-validator-mutant.FToGIP/test_validate_handbook.sh
```

Result: exit `1`. Relevant output:

```text
FAIL: latest inside an autolink destination passes
FAIL: unsupported superlative in README.md:11:<https://docs.example/latest/page>
PASS: latest in ordinary prose fails
PASS: latest in non-URL inline code fails
FAIL: 1 validator test(s) failed
```

This proves that the URL-only regression assertion detects removal of URL sanitization. The temporary mutant directory was deleted after the run.

## Final Implementation

The production change remains local to `check_unsupported_superlatives`:

```awk
scan = lower
gsub(/`\/[^`]*\/`/, "", scan)
gsub(/<https?:\/\/[^>]*>/, "", scan)
gsub(/https?:\/\/[^[:space:]>)]+/, "", scan)
gsub(/best-effort/, "", scan)
gsub(/always-on/, "", scan)
```

The order matters: Markdown URL-like content is removed from `scan`, but qualification checks still use the original lowercased line. Ordinary prose remains available to the banned-token expression even when the same line also contains a destination URL.

The implementation uses POSIX `awk`, shell `case`, and existing Bash 3.2-compatible constructs. It adds no dependency and performs no writes.

## Final Verification

### Full Validator Suite

Command:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Result: exit `0`, pristine output, and `PASS: all 27 validator tests passed`. The suite includes the original 24 cases, the interrupted worker's URL-only and ordinary-prose cases, and the audit's non-URL-inline-code case.

### Live Structure Validation With Explicit Root

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Result: exit `0` with eleven check-level `PASS:` lines and final output:

```text
PASS: structure validation completed with zero failures
```

### Live Structure Validation With Default Root

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure
```

Result: exit `0` with the same eleven check-level passes and final zero-failure line.

### Bash 3.2 Syntax Gate

```bash
/bin/bash --version
/bin/bash -n mlops/architect-handbook/scripts/validate_handbook.sh
/bin/bash -n mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Result: exit `0`; `/bin/bash` reported `GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)`, and both syntax checks produced no diagnostics.

## Changed Files

| File | Evidence | Change |
|---|---|---|
| `mlops/architect-handbook/scripts/validate_handbook.sh` | `4500483b8d537939671130a1cde1cb613ad1d0ff6b4612a1254fab53fffe787d` | Sanitizes HTTP(S) destinations and slash-delimited inline URL paths before superlative matching without hiding arbitrary inline code. |
| `mlops/architect-handbook/scripts/test_validate_handbook.sh` | `7a92ba41912dd8ef1e7f03006b179af567b24b04c862c13d4e9b269b6defddc6` | Adds URL-only, prose-plus-URL, and non-URL-inline-code regression fixtures; final count is 27. |
| `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-4-validator-url-bug-report.md` | Self-hash omitted because recording it would change the file | Documents diagnosis, reconstructed evidence, verification, and limitations. |

No research report or `mlops/vol1.md` was targeted by an audit write command. At the final read-only checkpoint, `mlops/vol1.md` had SHA-256 `53692a8c69dbf14d96d15a216b58c986dd0723bb750ddb74669c0b41ee433b12`, size `3,120,471` bytes, and modification time `2026-08-23T14:24:47+0530`. This is an end observation only; no start-state hash was captured during the interrupted worker's run, so no stronger immutability claim is made.

## Residual Limitations

- The sanitizer is deliberately bounded rather than a full CommonMark parser. It recognizes HTTP(S) autolinks, bare HTTP(S) destinations, and slash-delimited backticked path fragments.
- Non-HTTP schemes and arbitrary custom URI schemes are not excluded from the prose scan.
- The existing inline-link extractor's balanced-parenthesis and undefined-reference-label limitations are unchanged by this fix.
- Superlative qualification remains heuristic. Citation entailment and whether a constrained word is editorially justified still require human review.
- The pre-fix reproduction's backticked `` `/latest/` `` is treated as a URL-path fragment. Arbitrary inline code remains subject to the prose rule, as the new regression demonstrates.

## Changelog

### 2026-08-23

- Documented the validator URL false-positive root cause and the interrupted patch audit.
- Recorded the controlled-mutant proof, observed audit RED/GREEN cycle, full 27-case suite, live structure validations, and Bash 3.2 syntax gate.
