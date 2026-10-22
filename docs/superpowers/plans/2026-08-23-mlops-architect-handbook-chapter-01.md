# MLOps Architect Handbook Chapter 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the modular MLOps Architect Handbook framework and deliver a research-backed, publication-quality Chapter 1 for Senior/Staff/Principal readers without modifying the growing raw `mlops/vol1.md` manuscript.

**Architecture:** The maintained handbook lives under `mlops/architect-handbook/`, with one chapter per file, a controlled glossary, a bibliography and claim ledger, a diagram registry, and a deterministic local validator. Chapter 1 establishes the content and verification contract for later chapters; the raw manuscript remains an append-only external input and is observed only through metadata.

**Tech Stack:** Markdown, CSV, Mermaid/text diagrams, Bash 3.2-compatible shell, `rg`, `awk`, `sed`, `find`, `shasum`, authoritative web research, ECC deep-research/article-writing guidance, and Superpowers agent review.

**Spec:** `docs/superpowers/specs/2026-08-23-mlops-architect-handbook-chapter-01-design.md`

## Global Constraints

- Read `AGENTS.md`, `CLAUDE.md`, and the design spec before starting any task.
- Do not write to, rename, move, truncate, format, or roll back `mlops/vol1.md`.
- Record the raw manuscript's SHA-256, byte size, line count, and modification time at milestone start and end; concurrent growth is allowed and must be reported.
- Keep the handbook audience at Senior, Staff, and Principal MLOps / ML Platform Architect level.
- Never invent production evidence, benchmarks, scale, vendor behavior, or citations.
- Prioritize specifications, official documentation, peer-reviewed papers, and disclosed engineering case studies.
- Version-pin volatile product claims and give them an `as of` date plus review deadline.
- Distinguish sourced facts, reproducible calculations, illustrative scenarios, and author synthesis.
- Keep every maintained Markdown file compliant with the workspace changelog rules.
- Use ATX headings, CommonMark-compatible links, balanced fences, and ASCII hyphens in maintained handbook files.
- This workspace is not a Git repository. Do not initialize Git without user authorization; use task reports, validation output, and SHA-256 checkpoints instead of commit steps.
- Use `apply_patch` for repository file creation and edits.

## Table of Contents

1. [Task 1: Scaffold the handbook and record source state](#task-1-scaffold-the-handbook-and-record-source-state)
2. [Task 2: Build the validator with fixture-driven tests](#task-2-build-the-validator-with-fixture-driven-tests)
3. [Task 3: Define the editorial and publication contract](#task-3-define-the-editorial-and-publication-contract)
4. [Task 4: Research Chapter 1 with parallel specialist agents](#task-4-research-chapter-1-with-parallel-specialist-agents)
5. [Task 5: Build the evidence ledger and bibliography](#task-5-build-the-evidence-ledger-and-bibliography)
6. [Task 6: Draft Chapter 1 and its diagrams](#task-6-draft-chapter-1-and-its-diagrams)
7. [Task 7: Integrate navigation, glossary, and editorial status](#task-7-integrate-navigation-glossary-and-editorial-status)
8. [Task 8: Run independent reviews and the release gate](#task-8-run-independent-reviews-and-the-release-gate)

---

### Task 1: Scaffold the handbook and record source state

**Files:**

- Create: `mlops/architect-handbook/README.md`
- Create: `mlops/architect-handbook/EDITORIAL_STATUS.md`
- Create: `mlops/architect-handbook/STYLE_GUIDE.md`
- Create: `mlops/architect-handbook/GLOSSARY.md`
- Create: `mlops/architect-handbook/CHANGELOG.md`
- Create: `mlops/architect-handbook/chapters/.gitkeep`
- Create: `mlops/architect-handbook/sources/research/.gitkeep`
- Create: `mlops/architect-handbook/sources/references.md`
- Create: `mlops/architect-handbook/sources/claim-ledger.csv`
- Create: `mlops/architect-handbook/diagrams/chapter-01/README.md`
- Create: `mlops/architect-handbook/scripts/.gitkeep`

**Interfaces:**

- Consumes: `mlops/vol1.md` metadata through read-only shell commands.
- Produces: Stable directory contract and the `Raw source observations` table in `EDITORIAL_STATUS.md` used by Task 8.

- [ ] **Step 1: Capture the raw source baseline without writing to it**

Run:

```bash
shasum -a 256 mlops/vol1.md
wc -l -c mlops/vol1.md
stat -f 'mtime=%Sm bytes=%z' -t '%Y-%m-%dT%H:%M:%S%z' mlops/vol1.md
```

Expected: one SHA-256 value, line and byte counts, and a modification timestamp. Copy these exact values into the first row of `EDITORIAL_STATUS.md` under `Raw source observations` with event `Milestone start`.

- [ ] **Step 2: Create the directory skeleton and minimal documents**

Use `mkdir -p` only for directories and `apply_patch` for every file. Every maintained Markdown document must contain a `## Changelog` section. Use publication state `Scaffold` and Chapter 1 state `Planned`; do not claim draft or research completion.

- [ ] **Step 3: Initialize the claim-ledger schema exactly**

The first CSV row must be:

```csv
claim_id,chapter,section,claim_text,claim_type,risk_level,source_keys,source_version,source_date,accessed_date,status,review_by,notes
```

Allowed claim types are `normative`, `quantitative`, `product`, `scientific`, `security`, `architecture`, `scenario`, and `heuristic`. Allowed risk levels are `P0`, `P1`, `P2`, and `P3`. Initial status values may be `unverified`, `verified`, `qualified`, or `removed`.

- [ ] **Step 4: Verify the scaffold**

Run:

```bash
test -f mlops/architect-handbook/README.md
test -f mlops/architect-handbook/EDITORIAL_STATUS.md
test -f mlops/architect-handbook/STYLE_GUIDE.md
test -f mlops/architect-handbook/GLOSSARY.md
test -f mlops/architect-handbook/CHANGELOG.md
test -f mlops/architect-handbook/sources/references.md
head -n 1 mlops/architect-handbook/sources/claim-ledger.csv
rg --files-without-match '^## Changelog$' mlops/architect-handbook/*.md mlops/architect-handbook/diagrams/chapter-01/README.md mlops/architect-handbook/sources/references.md
```

Expected: every `test` exits 0, the CSV header exactly matches Step 3, and the final `rg --files-without-match` prints nothing.

- [ ] **Step 5: Record the task checkpoint**

Run `find mlops/architect-handbook -type f -print0 | sort -z | xargs -0 shasum -a 256` and save the output in the execution ledger for this plan. Do not create a Git commit.

---

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

### Task 3: Define the editorial and publication contract

**Files:**

- Modify: `mlops/architect-handbook/README.md`
- Modify: `mlops/architect-handbook/EDITORIAL_STATUS.md`
- Modify: `mlops/architect-handbook/STYLE_GUIDE.md`
- Modify: `mlops/architect-handbook/GLOSSARY.md`
- Modify: `mlops/architect-handbook/CHANGELOG.md`
- Modify: `mlops/architect-handbook/diagrams/chapter-01/README.md`

**Interfaces:**

- Consumes: directory contract from Task 1 and validation contract from Task 2.
- Produces: the binding chapter template, status model, citation format, diagram registry format, and navigation semantics used by Tasks 4-8.

- [ ] **Step 1: Write the canonical chapter template into `STYLE_GUIDE.md`**

Define the exact section sequence approved in the spec, the H1/H2/H3/H4 hierarchy, first-use acronym expansion, evidence-versus-synthesis labels, example formatting, callout syntax, and the banned generic phrases from ECC article-writing guidance. Require the pattern `problem -> constraints -> architecture -> trade-offs -> failure modes -> security -> cost -> operations -> decision framework -> exercises` where applicable.

- [ ] **Step 2: Define the publication lifecycle in `EDITORIAL_STATUS.md`**

Use exactly:

```text
Planned -> Researching -> Draft -> Technical Review -> Editorial Review -> Verified -> Publication Ready
```

Add columns for chapter, title, content state, evidence state, diagram state, technical review, editorial review, validator status, and last reviewed date. Chapter 1 remains `Planned` until Task 4 starts.

- [ ] **Step 3: Define diagram metadata**

In `diagrams/chapter-01/README.md`, require: figure ID, filename, section, purpose, assumptions, legend, provenance, alt text, semantic reviewer, and review status. List the planned figures `fig-01-ml-lifecycle`, `fig-02-architecture-planes`, `fig-03-systems-of-record`, and `fig-04-failure-propagation` as `Planned`.

- [ ] **Step 4: Establish navigation and reader contract in `README.md`**

State the Senior/Staff/Principal audience, Chapter 1 milestone, raw-source preservation rule, linked table of contents, reading-path design, evidence policy, and honest publication status. Do not list future chapters as completed.

- [ ] **Step 5: Seed only foundational glossary terms**

Add sourced or definition-pending rows for: MLOps, ML system, control plane, data plane, training plane, serving plane, model registry, artifact store, lineage, reproducibility, continuous training, service-level indicator, service-level objective, and architecture decision record. A term cannot be marked verified without a source key.

- [ ] **Step 6: Validate and checkpoint**

Run structure validation and `rg -n -i "game-changer|cutting-edge|revolutionary|in today's rapidly evolving landscape" mlops/architect-handbook`. Expected: validation exits 0 and the phrase scan returns no content matches outside explicit banned-pattern documentation. Record file hashes in the ledger.

---

### Task 4: Research Chapter 1 with parallel specialist agents

**Files:**

- Create: `mlops/architect-handbook/sources/research/chapter-01-foundations.md`
- Create: `mlops/architect-handbook/sources/research/chapter-01-governance-reliability.md`
- Create: `mlops/architect-handbook/sources/research/chapter-01-platform-strategy.md`

**Interfaces:**

- Consumes: Chapter 1 outline, evidence policy, and glossary contract from Task 3.
- Produces: three independent cited research reports whose source keys and claims are synthesized in Task 5.

- [ ] **Step 1: Dispatch three read-only research agents in parallel**

Use isolated contexts and one domain per agent:

1. **Foundations agent:** ML lifecycle, hidden technical debt, reproducibility, metadata, artifacts, feedback loops, and ML testing.
2. **Governance/reliability agent:** NIST AI RMF, security/governance plane, SLI/SLO boundaries, system-of-record integrity, and operational accountability.
3. **Platform-strategy agent:** platform/product ownership, Team Topologies/platform engineering concepts, build-versus-buy decision criteria, managed-service trade-offs, and Senior/Staff/Principal scope.

Each agent must search the live web, use only primary or authoritative sources for technical claims, read at least four key sources in full, and write its report to its assigned path. Each report must include methodology, exact source URLs, publication/update dates, accessed date `2026-08-23`, claim excerpts paraphrased in the agent's own words, applicability limits, unresolved conflicts, and a dated `## Changelog`. Agents must not edit any other file.

- [ ] **Step 2: Require the foundational source shortlist to be checked**

The research must attempt to verify and include or explicitly reject these sources:

- Sculley et al., *Hidden Technical Debt in Machine Learning Systems*
- Breck et al., *The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction*
- Google, *Rules of Machine Learning*
- NIST, *AI Risk Management Framework 1.0* and the current Playbook
- Google Cloud Architecture Center guidance on MLOps continuous delivery and automation pipelines
- AWS Well-Architected Machine Learning Lens
- Microsoft Azure Well-Architected Framework guidance for AI/ML workloads
- Kubernetes documentation for control-plane and workload concepts
- MLflow documentation for tracking and model-registry concepts
- CNCF or Linux Foundation platform-engineering guidance where it directly supports a claim

Sources that are obsolete, inaccessible, superseded, marketing-only, or unable to support the planned claim must be recorded as rejected with a reason.

- [ ] **Step 3: Review the three reports for source quality**

Confirm each report has at least four fully read authoritative sources, no bare search-result links, no unsourced quantitative claim, and explicit fact-versus-inference labeling. Send deficiencies back to the same agent for correction before Task 5.

- [ ] **Step 4: Update status and checkpoint**

Set Chapter 1 content state to `Researching`. Record report hashes and source counts in the execution ledger.

---

### Task 5: Build the evidence ledger and bibliography

**Files:**

- Modify: `mlops/architect-handbook/sources/references.md`
- Modify: `mlops/architect-handbook/sources/claim-ledger.csv`
- Modify: `mlops/architect-handbook/GLOSSARY.md`

**Interfaces:**

- Consumes: three reviewed research reports from Task 4.
- Produces: stable citation keys, verified claim rows, glossary sources, and a Chapter 1 evidence set consumed by Task 6.

- [ ] **Step 1: Create stable source keys**

Use uppercase keys in the form `ORG-SHORTTITLE-YEAR`, for example `NIST-AIRMF-2023` and `SCULLEY-TECHDEBT-2015`. Each bibliography entry must include title, author/organization, publication or update date, accessed date, stable URL or DOI, version when applicable, source class, and one sentence describing its supported scope.

- [ ] **Step 2: Populate claim rows before drafting prose**

Create unique IDs `CH01-C001`, `CH01-C002`, and so on. Each planned factual statement must have one row. Set `verified` only when the cited source entails the exact claim. Use `qualified` when the final prose must include explicit scope or assumptions. Use `removed` when evidence is insufficient and explain why in `notes`.

- [ ] **Step 3: Apply risk and freshness rules**

Classify security, normative, quantitative, product, and compatibility claims as P0 or P1 when errors would materially mislead readers. Give volatile claims a `review_by` date based on the design: 30 days for pricing/quotas/advisories, 90 days for product behavior, 180 days for security guidance, and one year or release-triggered review for foundational standards.

- [ ] **Step 4: Verify glossary definitions**

Every glossary term used in Chapter 1 must cite a stable source key or be labeled `Handbook synthesis`. Expand acronyms on first use in both glossary and chapter.

- [ ] **Step 5: Run evidence checks**

Run:

```bash
awk -F, 'NR==1 {next} $1 !~ /^CH01-C[0-9][0-9][0-9]$/ {print "bad claim id at row " NR; bad=1} END {exit bad}' mlops/architect-handbook/sources/claim-ledger.csv
awk -F, 'NR==1 {next} ($6=="P0" || $6=="P1") && $11!="verified" {print "unverified high-risk claim " $1; bad=1} END {exit bad}' mlops/architect-handbook/sources/claim-ledger.csv
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
```

Expected: all commands exit 0. Record claim counts by type and risk in the execution ledger.

---

### Task 6: Draft Chapter 1 and its diagrams

**Files:**

- Create: `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md`
- Create: `mlops/architect-handbook/diagrams/chapter-01/fig-01-ml-lifecycle.mmd`
- Create: `mlops/architect-handbook/diagrams/chapter-01/fig-02-architecture-planes.mmd`
- Create: `mlops/architect-handbook/diagrams/chapter-01/fig-03-systems-of-record.mmd`
- Create: `mlops/architect-handbook/diagrams/chapter-01/fig-04-failure-propagation.mmd`
- Modify: `mlops/architect-handbook/diagrams/chapter-01/README.md`

**Interfaces:**

- Consumes: verified claims and source keys from Task 5, plus the exact chapter contract from `STYLE_GUIDE.md`.
- Produces: complete Chapter 1 prose, four diagrams, exercises, interview rubric, references, and changelog entry.

- [ ] **Step 1: Create the full heading skeleton**

Use one H1 with the canonical title and H2 headings for all fifteen approved sections in the exact approved order. Add H3 headings only for architecture-plane types, maturity stages, system-of-record categories, decision dimensions, and Senior/Staff/Principal scope.

- [ ] **Step 2: Draft Sections 1-6 from verified claims**

Cover outcomes, prerequisites, production ML as a systems problem, lifecycle feedback loops, the seven architecture planes, a capability maturity model, and systems of record. Every major concept must include a concrete example, assumptions, trade-offs, a failure mode, and forward references where later chapters own the details.

- [ ] **Step 3: Draft Sections 7-11 as architecture decision material**

Define platform/product responsibilities, build-buy-managed criteria, role-scope distinctions, reference architecture flows, and one production failure case. The case must identify trigger, propagation path, detection signals, containment, recovery, and preventive controls without presenting an invented company incident as fact.

- [ ] **Step 4: Draft Sections 12-15 as assessment and reference material**

Include one architecture decision record exercise with explicit context and constraints, at least twelve interview questions split across Senior/Staff/Principal expectations, a scoring rubric with observable signals, concise takeaways, glossary links, chapter citations, and a `## Changelog`.

- [ ] **Step 5: Create and register four diagrams**

Use Mermaid flowcharts that render without external images. Each figure registry entry must contain purpose, assumptions, legend, `Original handbook synthesis` provenance unless adapted, meaningful text alternative, and status `Technical Review`. Ensure component names match the prose and arrows distinguish control, data, artifact, and telemetry flow.

- [ ] **Step 6: Run draft checks**

Run:

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
rg -n -i "game-changer|cutting-edge|revolutionary|in today's rapidly evolving landscape|here's why this matters" mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md
rg -n '```text id=' mlops/architect-handbook
```

Expected: structure validation exits 0 and both phrase/artifact scans return no matches. Set Chapter 1 state to `Draft` only after these checks pass.

---

### Task 7: Integrate navigation, glossary, and editorial status

**Files:**

- Modify: `mlops/architect-handbook/README.md`
- Modify: `mlops/architect-handbook/EDITORIAL_STATUS.md`
- Modify: `mlops/architect-handbook/GLOSSARY.md`
- Modify: `mlops/architect-handbook/CHANGELOG.md`
- Modify: `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md`

**Interfaces:**

- Consumes: complete draft and diagrams from Task 6.
- Produces: resolvable navigation, consistent terminology, accurate lifecycle state, and release-candidate documentation.

- [ ] **Step 1: Link the handbook index to Chapter 1**

Add the exact relative link `chapters/01-mlops-architecture-foundations.md`, a one-sentence purpose, prerequisites, and state. Do not add links to unwritten chapters.

- [ ] **Step 2: Resolve glossary and cross-reference anchors**

Confirm every Chapter 1 glossary link resolves, every acronym expands on first use, and later-chapter references are plain-language scope notes rather than broken links to nonexistent files.

- [ ] **Step 3: Synchronize publication state**

Set Chapter 1 to `Technical Review`, evidence to `Verified` only if all P0/P1 rows pass, diagrams to `Technical Review`, and validator to the latest actual result. Update all material changelogs with August 23, 2026 entries.

- [ ] **Step 4: Run structure validation and a link audit**

Run:

```bash
bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
rg -n '\]\([^)]*\.md[^)]*\)' mlops/architect-handbook
```

Expected: validator exits 0. Manually open every Markdown target printed by the second command and confirm its file and anchor exist.

- [ ] **Step 5: Record the task checkpoint**

Record hashes for all maintained handbook files and the structure-validation output in the execution ledger.

---

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
