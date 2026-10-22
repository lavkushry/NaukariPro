# Task 8 Editorial and Accessibility Rereview

## Verdict

**REQUEST CHANGES — not approved.**

- Critical: 0
- Important: 1
- Minor: 2

Approval requires zero Critical and zero Important findings. I1, I2, I4, I5, M1, M2, and M3 are resolved. I3 is only partially resolved: prose cadence improved, but the required concise takeaway section did not.

## Scope

This focused independent rereview read the prior Task 8 editorial review, the editorial, evidence, and technical correction reports, the complete live Chapter 1, handbook README, editorial status, glossary, diagram registry and text alternatives, style guide, and complete Task 8 review-package diff. It checked the corrected finding set, cross-domain regressions, publication voice, navigation, accessibility, evidence boundaries, exercises, interview evaluation, and changelogs. No handbook file was edited.

## Finding resolution

| Prior finding | Status | Rereview evidence |
| --- | --- | --- |
| I1 — chapter navigation | Resolved | Chapter `:5-10` contains 16 links: the 15 substantive H2 sections plus Changelog. All 16 targets resolve. |
| I2 — figure alternatives | Resolved | Chapter `:67`, `:106`, `:238`, and `:485` place a diagram-source link and text-alternative link together at point of use. All four alternative links resolve to the stable registry headings at registry `:26`, `:39`, `:52`, and `:65`; the alternatives communicate flow, authority, state, and failure meaning without relying on color or shape. |
| I3 — cadence and concise takeaways | **Partially resolved; Important remains** | Long physical paragraphs and mechanical forward-boundary repetition are corrected, but Chapter `:642-660` is still a 322-word recap with eight decision bullets followed by six full, cited synthesis bullets. |
| I4 — ADR usability | Resolved | Chapter `:539-570` supplies a bounded scenario, explicit withheld inputs, provisional lower/higher sensitivity cases, reversal conditions, blocker/provisional/firm guidance, and a decision-complete 12-field checklist. |
| I5 — interview scoring | Resolved, with one Minor clarification below | Chapter `:576-624` has 18 questions and 18 corresponding evidence maps, each with must-have signals, relevant dimensions, and a disqualifying omission. Neutral follow-up, partial-answer, role-calibration, and observable scoring guidance appear at `:626-638`. |
| M1 — inaccessible dense tables | Resolved | The Chapter register is a vertical record (`EDITORIAL_STATUS.md:16-26`); all 14 glossary entries are linear term blocks; chapter responsibility and sourcing comparisons are linear. The raw-source observation table remains appropriate data, and Chapter 1 retains only the simple two-column scoring rubric. |
| M2 — changelog heading | Resolved | Chapter `:696-698` uses `## Changelog` and `### 2026-08-23`. |
| M3 — README policy navigation | Resolved | README `:27` links the phrase “evidence policy” to `#evidence-and-publication-policy`. |

## Important finding

### I3. The takeaway section remains repetitive rather than concise

**Location:** `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:642-660`.

The cadence repair elsewhere is effective: `Later chapters own` fell from 26 occurrences to 3, no physical line exceeds 80 words, and the 45 required `Handbook synthesis (bounded)` labels remain at point of use. The takeaways, however, grew from roughly 314 words in the reviewed version to 322 words. The eight concise decision rules at `:644-651` already perform the required wrap-up. The six-item blockquote at `:653-660` then restates lifecycle, canonical records, ownership, sourcing, role scope, and reliability distinctions already established in the chapter and partly duplicates the immediately preceding bullets. Repeating “Handbook synthesis (bounded)” six times in one closing block also restores the mechanical cadence the correction was meant to remove.

**Concrete fix:** Keep the eight short decision rules. Replace the six-item blockquote with one compact bounded-synthesis statement that qualifies the list as a whole, or remove the duplicated claims and direct readers to the earlier point-of-proof sections or coverage appendix. Preserve the evidence boundary and citations where they are substantively required; do not delete point-of-use qualifications from the body.

## Minor findings

### M4. A new H3 exceeds the exact Chapter 1 heading contract

**Location:** Chapter `:603`, `### Question-to-evidence map`.

Task 6's exact contract permits H3 headings only for architecture-plane types, maturity stages, system-of-record categories, sourcing decision dimensions, and Senior/Staff/Principal scope. The correction adds a sixth H3 category. The content is useful and belongs in the interview section, but its heading level is a cross-domain structural regression.

**Concrete fix:** Change it to an inline label such as `**Question-to-evidence map:**` while preserving the complete 18-item map. The ATX changelog date remains the separately required changelog convention.

### M5. “Cannot pass” lacks an explicit scoring consequence

**Location:** Chapter `:626`.

The new guidance says an answer “cannot pass a disqualifying omission,” while the rubric assigns scores 1-5 and the role calibration gives expected levels. It does not say whether the omission caps the score, overrides the role threshold, or requires a second neutral probe. Different interviewers can therefore apply the same evidence map differently.

**Concrete fix:** Define one observable consequence, for example that an unresolved question-specific disqualifying omission caps the answer below the role's passing level after the single neutral follow-up. State the exact cap or rule; keep the instruction to score only demonstrated evidence.

## Accessibility and publication-voice assessment

- The four figures have adjacent source/alternative associations and valid targets; their alternatives describe sequence, authority, data and control distinctions, feedback, containment, and recovery in linear prose.
- Status, glossary, responsibility, and sourcing content now works in a linear reading order. The remaining two-column rubric has descriptive row labels and does not depend on visual position alone.
- Acronym expansion, scenario labeling, assumptions, trade-offs, failure modes, forward boundaries, source qualifications, and Senior/Staff/Principal decision horizons remain intact.
- The chapter's publication voice is appropriately architectural and evidence-aware for Senior, Staff, and Principal readers. Outside the takeaway duplication, the correction reduces generated-sounding template repetition without weakening evidence or major-concept treatment.
- No inaccessible custom heading IDs, unwritten-chapter links, banned phrases, or unresolved maintained-content markers were found.

## Verification evidence

```text
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
exit 0; 27/27 validator tests passed

bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
exit 0; zero failures

bash mlops/architect-handbook/scripts/validate_handbook.sh --profile release mlops/architect-handbook
exit 0; zero failures
```

Focused corroboration:

```text
TOC_LINKS=16; MISSING_TOC_TARGETS=0
FIGURE_SOURCE_ALT_PAIRS=4; MISSING_ALT_TARGETS=0
REGISTRY_TEXT_ALTERNATIVES=4
ADR_CHECKBOX_FIELDS=12
QUESTION_EVIDENCE_MAPS=18
LONG_PHYSICAL_LINES_GT80_WORDS=0
KEY_TAKEAWAY_WORDS=322
GLOSSARY_TABLE_ROWS=0
CHAPTER_REGISTER_TABLE_ROWS=0
TASK8_REVIEW_PACKAGE_MATCHES_LIVE_DIFF=yes
```

The literal marker and generated-ID scans report only the validator implementation and intentional negative-test fixtures under `scripts/`; maintained-content scans excluding scripts return zero. The banned-phrase scan returns zero. The packaged diff reproduces the live handbook delta exactly, and live corrected-file hashes match the editorial correction report.

## Approval gate

The correction set is close, and no Critical issue remains. Editorial approval is still blocked by I3. After the takeaway section is made genuinely concise, rerun the validator profiles and focused anchor/content counts; M4 and M5 should be corrected in the same pass.

## Changelog

### 2026-08-23

- Completed the independent focused Task 8 editorial and accessibility rereview, verified prior finding resolutions and regressions, recorded validation evidence, and withheld approval for one remaining Important finding.
