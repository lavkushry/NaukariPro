# Task 2 Fix Round 1 Re-Review

## Per-Finding Verdict

### 1. Exit-status wraparound at exactly 256 failures

**ADDRESSED.** `exit_with_failures` preserves the full `FAILURES` value for reporting while clamping every value above 255 to process status 255, and every failure exit path now uses that helper (`mlops/architect-handbook/scripts/validate_handbook.sh:25-33,610-637,659-665`). The focused 256-defect fixture asserts both failure and the complete reported count (`mlops/architect-handbook/scripts/test_validate_handbook.sh:162-171`), matching the controller's successful 19-test evidence (`.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-2-report.md:106-128`).

### 2. Diagram gate accepts duplicate or non-approved targets

**NOT ADDRESSED.** The new counter does reject duplicates and arbitrary targets, but its approval set is inconsistent with the binding downstream contract. It hard-codes `ml-lifecycle.mmd`, `architecture-planes.mmd`, `system-of-record.mmd`, and `failure-flow.mmd` (`mlops/architect-handbook/scripts/validate_handbook.sh:8-11,126-195`), while Task 6 must create `fig-01-ml-lifecycle.mmd`, `fig-02-architecture-planes.mmd`, `fig-03-systems-of-record.mmd`, and `fig-04-failure-propagation.mmd` (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:365-374`). Task 3's approved figure identifiers use the same Task 6 stems (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:254-256`). The fixture was updated only around negative cases and still creates/registers the obsolete filenames, so its release-pass result proves the wrong contract (`mlops/architect-handbook/scripts/test_validate_handbook.sh:59-71,157-160`). A correctly implemented Task 6 would therefore fail release validation.

### 3. Reference-style links and duplicate-heading suffix anchors unsupported

**ADDRESSED for the original named cases.** Reference-definition destinations are now extracted and checked (`mlops/architect-handbook/scripts/validate_handbook.sh:54-86,466-505`), and duplicate ATX headings receive deterministic `-1`, `-2`, and later suffixes (`mlops/architect-handbook/scripts/validate_handbook.sh:88-117`). The new negative reference-destination and positive duplicate-anchor fixtures exercise those exact behaviors (`mlops/architect-handbook/scripts/test_validate_handbook.sh:203-214`). A fix-induced fenced-example problem remains under New Breakage.

### 4. Missing heading hierarchy, placeholder, generic phrase, and unsupported-superlative checks

**ADDRESSED for presence and dispatch.** The fix adds all four deterministic checks, excludes `scripts/`, skips exact triple-backtick fenced bodies for these prose checks, and invokes them in both profiles (`mlops/architect-handbook/scripts/validate_handbook.sh:50-52,264-306,352-464,643-653`). The four focused fixtures cover one invalid hierarchy, one placeholder, one generic phrase, and one unsupported superlative (`mlops/architect-handbook/scripts/test_validate_handbook.sh:216-238`). This meets the categories required by the approved validation design (`docs/superpowers/specs/2026-08-23-mlops-architect-handbook-chapter-01-design.md:179-193`), although one new false-positive class remains below.

## New Breakage

### Critical

None.

### Important

1. **The new diagram allowlist blocks the approved Task 6 deliverables and bans unrelated valid registry links.** Beyond using the wrong four filenames, `check_registered_diagrams` treats every relative link in the registry as a diagram candidate and fails any non-allowlisted target (`mlops/architect-handbook/scripts/validate_handbook.sh:130-160`). The registry contract includes a `section` field and may legitimately link a figure to its Chapter 1 section; general link validation should check such navigation without the diagram gate labeling it an unapproved diagram (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:254-256,397-399`). Match the four exact Task 6 `.mmd` filenames, require each once, and leave other valid relative links to `check_relative_links`.

2. **New reference/duplicate-anchor handling treats fenced Markdown examples as rendered links and headings.** `extract_markdown_targets` recognizes reference definitions without tracking fence state, so a fenced example such as `[guide]: missing.md` now creates a false broken-link failure (`mlops/architect-handbook/scripts/validate_handbook.sh:54-85`). `heading_anchor_exists` likewise counts ATX-looking lines inside fences when allocating duplicate suffixes, which can accept a nonexistent fenced anchor or shift a real repeated heading from `#name` to `#name-1` (`mlops/architect-handbook/scripts/validate_handbook.sh:88-117`). This is material because the handbook design explicitly uses fenced Markdown templates containing ATX-looking lines (`docs/superpowers/specs/2026-08-23-mlops-architect-handbook-chapter-01-design.md:122-132`). Both functions should ignore fenced bodies using the same fence-state rule as the new hierarchy/prose checks.

3. **The placeholder gate confuses policy documentation with unresolved content.** The regex fails every prose occurrence of the standalone word `placeholder`, regardless of context (`mlops/architect-handbook/scripts/validate_handbook.sh:352-385`). Consequently, legitimate policy or changelog text such as “placeholder text is forbidden” or “removed placeholder text” fails validation even though it documents resolution rather than containing a placeholder. The plan expressly anticipates explicit banned-pattern documentation as an allowed exception (`docs/superpowers/plans/2026-08-23-mlops-architect-handbook-chapter-01.md:266-268`). Restrict this check to actual placeholder forms or define a deterministic documentation exclusion; the current fenced-only escape is not semantically sufficient.

## Out-of-Scope Observations

- The original Minor coverage gaps for P0 versus P1, `qualified`/`removed` release status, marker exclusion under `scripts/`, and other CommonMark destination forms were not part of this fix-round verdict. The new suite still uses one P1 `unverified` row for the release-claim negative (`mlops/architect-handbook/scripts/test_validate_handbook.sh:142-149`).
- The reference-style fix validates definition destinations but does not detect an undefined reference label used by prose, and the inline extractor still does not parse balanced parentheses in destinations (`mlops/architect-handbook/scripts/validate_handbook.sh:54-85`). These remain lower-priority parser limitations outside the two exact link cases assigned to Fix Round 1.
- Per controller instruction, the successful 19-test harness and real structure run were accepted as evidence and were not rerun (`.superpowers/sdd/2026-08-23-mlops-architect-handbook-chapter-01/task-2-report.md:94-145`).

## Round Verdict

**REQUEST CHANGES.** Findings 1, 3, and 4 are addressed for their original named behaviors. Finding 2 is not addressed because the validator and fixtures enforce filenames that conflict with Task 6's exact diagram deliverables. The fix also introduces Important false-positive paths for fenced Markdown examples and legitimate placeholder-policy documentation. Correct the diagram contract and fence/documentation handling, then add focused regression fixtures before another round.

## Changelog

### August 23, 2026

- Re-reviewed Fix Round 1 against the four original Important findings and the fix-only diff.
- Recorded three addressed findings, one not-addressed finding, no new Critical issues, and three new Important breakages.
