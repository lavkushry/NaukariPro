### Task 2: Build the validator with fixture-driven tests

**Files:**

- Create: `mlops/architect-handbook/scripts/test_validate_handbook.sh`
- Create: `mlops/architect-handbook/scripts/validate_handbook.sh`

**Interfaces:**

- Consumes: handbook root path and optional profile.
- Produces: `validate_handbook.sh [--profile structure|release] [HANDBOOK_ROOT]`, human-readable `PASS`/`FAIL` lines, and exit code `0` only when the selected profile passes.

- [ ] **Step 1: Write executable validator tests before the validator**

The test script must create isolated fixtures under `mktemp -d`, clean them with `trap`, and assert these exact behaviors:

1. A complete minimal fixture passes `--profile structure`.
2. A missing required file fails and names that file.
3. An unbalanced Markdown fence fails and names the affected file.
4. A fence opener containing `id="generated"` fails.
5. An unresolved marker token (`TODO`, `TBD`, `FIXME`, or `VERIFY`) fails outside the validator documentation itself.
6. A broken relative Markdown link fails and names the target.
7. A malformed claim-ledger header fails.
8. A `P0` or `P1` Chapter 1 ledger row with `unverified` status fails `--profile release`.
9. A maintained Markdown file without `## Changelog` fails.
10. A complete release fixture passes `--profile release`.

Implement test helpers with these signatures:

```bash
assert_pass() {
  description="$1"
  shift
  if output=$("$@" 2>&1); then
    printf 'PASS: %s\n' "$description"
  else
    printf 'FAIL: %s\n%s\n' "$description" "$output"
    return 1
  fi
}

assert_fail_contains() {
  description="$1"
  expected="$2"
  shift 2
  if output=$("$@" 2>&1); then
    printf 'FAIL: %s - command unexpectedly passed\n' "$description"
    return 1
  fi
  if printf '%s\n' "$output" | grep -Fq "$expected"; then
    printf 'PASS: %s\n' "$description"
  else
    printf 'FAIL: %s - missing output: %s\n%s\n' "$description" "$expected" "$output"
    return 1
  fi
}
```

`make_valid_fixture FIXTURE_ROOT` must create the required directory tree, five root Markdown files containing `## Changelog`, a Chapter 1 file containing all fifteen required H2 headings and `## Changelog`, `sources/references.md`, the exact ledger header from Task 1 plus one `CH01-C001` verified P1 row, and a diagram-registry Markdown file. It must use only its temporary fixture path and must never write into the real handbook.

- [ ] **Step 2: Run tests and confirm the red state**

Run:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Expected: non-zero exit with the first assertion reporting that `validate_handbook.sh` is absent or non-executable.

- [ ] **Step 3: Implement the minimal deterministic validator**

Use Bash 3.2-compatible syntax. Define `fail MESSAGE` to increment a global failure count and print `FAIL: MESSAGE`; define `pass MESSAGE` to print `PASS: MESSAGE`. Implement these exact check contracts:

| Function | Required algorithm |
|---|---|
| `check_required_files` | In `structure`, require the five root Markdown files, `sources/references.md`, `sources/claim-ledger.csv`, and the diagram registry. In `release`, additionally require the Chapter 1 file and all four registered diagram files. Call `fail` once for every missing regular file. |
| `check_changelogs` | Find every maintained `*.md` file under the handbook root; require an exact `## Changelog` heading in each. |
| `check_fences` | For every Markdown file, count lines beginning with three backticks using `awk`; fail when the count is odd. |
| `check_generated_ids` | Search Markdown fence openers for the regular expression `id="[^"]+"`; report each matching file and line. |
| `check_markers` | Search maintained content outside `scripts/` for the four unresolved marker tokens listed in Step 1; report file and line. |
| `check_relative_links` | Extract relative Markdown targets, remove anchors and query strings, ignore HTTP(S), mail, and same-document anchors, resolve paths from the containing document, and fail for missing files or missing ATX-heading anchors. |
| `check_ledger_schema` | Compare the first line byte-for-byte with the Task 1 CSV header and fail on mismatch. |
| `check_release_claims` | Parse the CSV header positions, then fail every Chapter 1 P0/P1 row whose status is not `verified`; also require all fifteen approved Chapter 1 H2 headings. |

The script must be read-only, quote all paths, reject unknown profiles, and default to `--profile release`. `structure` checks required files, changelogs, fences, generated IDs, markers, relative links, and ledger schema. `release` runs all structure checks plus unresolved P0/P1 claims and Chapter 1 required-section checks. Exit with the accumulated non-zero failure count after all checks so one run reports every defect.

- [ ] **Step 4: Run the tests to confirm the green state**

Run:

```bash
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
```

Expected: ten named assertions pass and the script exits 0.

- [ ] **Step 5: Verify the real scaffold in structure mode**

Run:

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Expected: exit 0 with no `FAIL:` lines.

- [ ] **Step 6: Record the task checkpoint**

Record SHA-256 values for both scripts and the full test output in the execution ledger. Do not create a Git commit.

---

