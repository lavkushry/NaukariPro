### Task 8: Run independent reviews and the release gate

**Files:**

- Modify as findings require: `mlops/architect-handbook/**`
- Modify: `mlops/architect-handbook/EDITORIAL_STATUS.md`
- Modify: `mlops/architect-handbook/CHANGELOG.md`

**Interfaces:**

- Consumes: integrated Chapter 1 release candidate from Task 7.
- Produces: reviewed handbook milestone, final validation evidence, raw-source end observation, and an honest `Publication Ready` or `Review Required` state.

- [ ] **Step 1: Dispatch independent specialist reviews**

Use separate agents with isolated contexts:

1. **Technical architecture reviewer:** correctness, component boundaries, data/control flows, failure modes, trade-offs, and Senior/Staff/Principal calibration.
2. **Evidence reviewer:** citation entailment, primary-source quality, claim-ledger coverage, dates, versions, and unsupported assertions.
3. **Editorial reviewer:** structure, repetition, voice, navigation, accessibility, glossary consistency, and exercise/interview usefulness.

Each reviewer must write a report under the execution workspace, classify findings as Critical, Important, or Minor, and avoid editing handbook files. Critical and Important findings require correction and scoped re-review before release.

- [ ] **Step 2: Apply and re-review corrections**

Use one implementer at a time to avoid shared-file conflicts. For each finding, record the source report, affected file, resolution, validation command, and reviewer verdict in the execution ledger. Do not dismiss evidence gaps by weakening the validator.

- [ ] **Step 3: Run the final release validator**

Run:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile release mlops/architect-handbook
```

Expected: every named validator test passes (24 tests at the end of Task 2), release validation exits 0, and no `FAIL:` line appears. Report the observed test count if later regression cases increase it.

- [ ] **Step 4: Run final content scans**

Run:

```bash
rg -n -i '\b(TODO|TBD|FIXME|VERIFY)\b' mlops/architect-handbook --glob '!scripts/**'
rg -n '```[^`]*id="' mlops/architect-handbook
rg -n -i "game-changer|cutting-edge|revolutionary|in today's rapidly evolving landscape" mlops/architect-handbook/chapters
```

Expected: no matches.

- [ ] **Step 5: Record the raw source end observation**

Run:

```bash
shasum -a 256 mlops/vol1.md
wc -l -c mlops/vol1.md
stat -f 'mtime=%Sm bytes=%z' -t '%Y-%m-%dT%H:%M:%S%z' mlops/vol1.md
```

Append the exact values to `EDITORIAL_STATUS.md` with event `Milestone end`. If the raw file grew, report the change without rollback; verify from the execution ledger that no implementation patch or command targeted it.

- [ ] **Step 6: Set the honest final status**

Set `Publication Ready` only when release validation passes, all Critical and Important review findings are closed, diagrams are technically approved, and P0/P1 claims are verified. Otherwise set `Review Required` and list each remaining gate without claiming completion.

- [ ] **Step 7: Produce the final verification report**

Report validator test count, release result, claim counts by risk/status, source count, diagram review state, link status, unresolved findings, files created/modified, and raw-source start/end observations. Record final file hashes in the execution ledger. Do not create a Git commit.

## Changelog

### August 23, 2026

- Created the task-by-task implementation plan for the handbook framework and Chapter 1 milestone.
- Added agent-based research and independent review, claim-ledger construction, fixture-driven validation, diagrams, navigation, and release gates.
- Replaced unavailable Git checkpoints with explicit SHA-256 and execution-ledger evidence.
