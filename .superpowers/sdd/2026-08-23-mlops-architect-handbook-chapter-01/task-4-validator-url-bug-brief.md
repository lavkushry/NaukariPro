# Task 4 Validator URL False-Positive Bug

## Objective

Correct the handbook validator so banned superlative checks inspect prose but do not flag a banned token that appears only inside a Markdown destination URL, including autolinks such as `<https://docs.example/latest/page>`.

## Reproduction

Running:

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

incorrectly flags `latest` inside official MLflow and AWS documentation URLs in the three Task 4 research reports.

## Required process

1. Read `AGENTS.md`, `CLAUDE.md`, the design spec, Task 2 plan section, the validator and complete validator test suite.
2. Read and apply the Superpowers systematic-debugging, test-driven-development, and verification-before-completion skills.
3. Reproduce and document the root cause.
4. RED: add the smallest regression fixture proving a URL-only `latest` token must pass while ordinary prose containing banned `latest` must still fail; run it and observe the expected failure before implementation.
5. GREEN: make the smallest robust parser change.
6. Run the full test suite and both relevant structure validation commands.

## Write scope

- `mlops/architect-handbook/scripts/validate_handbook.sh`
- `mlops/architect-handbook/scripts/test_validate_handbook.sh`
- `.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-4-validator-url-bug-report.md`

Do not edit research reports or `mlops/vol1.md`. Do not initialize Git. Do not spawn subagents.

## Acceptance criteria

- The new regression test is observed failing before the production change and passing afterward.
- Banned prose is still rejected.
- Official URLs containing `/latest/` do not trigger the prose superlative rule.
- The full validator test suite has pristine output and all tests pass.
- Structure validation passes on the live handbook.
- The report records commands, RED/GREEN evidence, files changed, and residual limitations.

## Changelog

### 2026-08-23

- Added a bounded TDD bug-fix brief for URL-only superlative false positives.
