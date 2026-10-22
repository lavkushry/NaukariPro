# Task 4 Research Checkpoint Report

## Outcome

Task 4 is complete. Chapter 1 moved from `Planned` to `Researching` after three parallel, scope-separated research reports were corrected against the combined review. The reports are research inputs for Task 5; this checkpoint does not claim that a chapter draft, claim ledger, diagrams, technical review, editorial review, verification, or publication approval exists.

## Research fan-out and source counts

| Research domain | Report | Declared authoritative evidence |
| --- | --- | --- |
| Foundations | `chapter-01-foundations.md` | 8 accepted sources |
| Governance and reliability | `chapter-01-governance-reliability.md` | 5 substantive source sets; 7 source-register entries |
| Platform strategy | `chapter-01-platform-strategy.md` | 9 fully read key pages |

The planned fan-out used three specialist agents with disjoint write paths and a controller-owned integration checkpoint. The combined research set dispositions the required shortlist and keeps source facts separate from handbook synthesis.

## Fresh report hashes

Computed after the research-report fixes:

```text
b4a36b1db7eb27a4a9933416c84238c22d7f0e4cc5c025edd81dcbcaab6b87e1  mlops/architect-handbook/sources/research/chapter-01-foundations.md
914fd26c4444866b706f05cd4ccc668853f304945c82f34dd6be37adae7feefa  mlops/architect-handbook/sources/research/chapter-01-governance-reliability.md
b0c83379ef1d85e34fec787f6ed6cdf93b547f9a3c5e83c1e52cec11142d6d33  mlops/architect-handbook/sources/research/chapter-01-platform-strategy.md
```

## Review reconciliation

The combined review initially requested changes: 0 Critical, 2 Important, and 1 Minor finding.

- The platform report now labels the conclusion that automation alone does not establish governance or reliability as **Handbook synthesis**, separate from the AWS-supported design-principles fact, with an explicit assumption.
- The governance/reliability report now uses the controlled `service-level indicator (SLI)` and `service-level objective (SLO)` expansions.
- This checkpoint fixes the remaining controller finding by recording the `Researching` status, source counts, and fresh corrected-report hashes.

These corrections resolve Task 4 findings only. Claim-level verification and all later release gates remain pending.

## Validator audit and verification

The URL false-positive audit changed the prose-superlative scan to ignore HTTP(S) destinations and slash-delimited inline URL paths while retaining rejection of ordinary prose and non-URL inline-code `latest` tokens. Its controlled-mutant and RED/GREEN evidence are recorded in `task-4-validator-url-bug-report.md`.

Final commands:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Result: 27/27 validator tests passed and live structure validation completed with zero failures. These checks validate the scaffold and research checkpoint only; release validation is not applicable before Chapter 1 content and diagrams exist.

## Scope and raw-source integrity

Only this report, the execution ledger, and editorial status were changed by the integration checkpoint. `mlops/vol1.md` was not edited. Because the raw manuscript may grow externally, this report makes no unsupported unchanged-file claim.

## Changelog

### 2026-08-23

- Recorded Task 4 source-count reconciliation, corrected-report hashes, reviewer-finding resolution, validator URL audit, and structure-only validation outcome.
