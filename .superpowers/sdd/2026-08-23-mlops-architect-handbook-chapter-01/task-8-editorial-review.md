# Task 8 Independent Editorial and Accessibility Review

## Verdict

**REQUEST CHANGES — not approved.** The review found **0 Critical, 5 Important, and 3 Minor** findings. Chapter 1 satisfies the required section sequence and contains the required architecture material, but it does not yet meet the publication-quality editorial and accessibility gate. Approval requires zero unresolved Critical or Important findings.

## Review scope

This review read the workspace instructions, approved design, Task 8 brief, ECC article-writing skill, handbook style guide, handbook index, editorial status, glossary, complete 519-line Chapter 1, all four Mermaid sources, diagram registry and text alternatives, bibliography, Task 6 review and rereview, and Task 7 review. It assessed the exact section contract, information architecture, Senior/Staff/Principal voice, repetition, paragraph flow, headings, terminology and acronym expansion, links, accessibility, scenario labels, forward boundaries, ADR exercise, all 18 interview questions, observable rubric, takeaways, citations, and changelogs. No handbook file was edited.

## Contract and quality summary

| Area | Result |
| --- | --- |
| Required H1/H2 sequence | Pass: one canonical H1; all 15 required H2 sections appear in the approved order; `## Changelog` follows them |
| Required content | Pass: seven planes, five maturity stages, six record groups, responsibility and sourcing models, role scope, lifecycle flow, bounded failure case, ADR exercise, 18 questions, rubric, takeaways, glossary, references, and changelog are present |
| Audience and voice | Partial: technically calibrated for Senior/Staff/Principal readers, but repeated sentence templates and dense paragraph packaging weaken the sharp operator voice |
| Terminology and acronyms | Pass: controlled terms are consistent and first-use expansions are present; no conflicting controlled definition was found |
| Scenarios and forward boundaries | Pass with editorial qualification: fictional examples are bounded, but forward-boundary language is repeated mechanically rather than organized for flow |
| Navigation and links | Automated pass; Important chapter-level navigation and figure-accessibility defects remain |
| Tables | Structurally valid Markdown; several wide tables need a linear-access alternative or a more accessible form |
| Assessment material | Complete in count; Important usability defects remain in the ADR inputs and question-to-rubric mapping |
| Changelogs | Present in maintained files; one Chapter 1 date label is inconsistent with the ATX convention |

## Findings

### Critical

None.

### Important

#### I1. The 519-line chapter has no table of contents

**Locations:** `mlops/architect-handbook/chapters/01-mlops-architecture-foundations.md:1-3` and all H2 headings through `:511`.

The workspace rule requires a table of contents for documents longer than 200 lines. Chapter 1 has 519 lines, approximately 9,852 words, and 15 substantive H2 sections, yet the reader moves directly from the title into outcomes. The handbook README has its own table of contents, but it does not provide in-chapter navigation. This is a material scanability and keyboard-navigation defect for a long technical chapter.

**Concrete fix:** Add a compact linked table of contents inside `## Reader outcomes and prerequisites`, before the outcomes list. Use a bold inline label rather than a new H2 or H3 so the exact Task 6 heading contract remains unchanged. Link all 15 approved sections and the changelog using the validator's existing ATX anchor rules.

#### I2. Figure text alternatives exist but are not associated with the figures in the chapter

**Locations:** Chapter figure references at `01-mlops-architecture-foundations.md:54`, `:87`, `:179`, and `:360`; text alternatives at `diagrams/chapter-01/README.md:35`, `:48`, `:61`, and `:74`.

Each chapter reference links only to a raw `.mmd` source. The chapter never links to or reproduces the corresponding text alternative. A reader following the chapter, including a screen-reader or non-Mermaid reader, receives Mermaid syntax rather than the concise semantic alternative already maintained in the registry. The alternatives satisfy the registry metadata contract but are not discoverably associated with their figures at the point of use.

**Concrete fix:** For every figure citation, provide separate adjacent links labeled `Diagram source` and `Text alternative`, with the latter targeting the exact registry entry. Give registry entries stable anchors based on figure IDs, or include the full text alternative immediately after each figure reference. The publication renderer must associate the same alternative with any rendered image; do not make color or arrow shape the only carrier of meaning.

#### I3. Repeated templates overwhelm paragraph flow and make the takeaways non-concise

**Locations:** Architecture planes `:91-135`; maturity stages `:143-173`; record groups `:183-219`; decision dimensions `:255-283`; role scopes `:302-328`; takeaways `:466-477`.

The chapter uses `Later chapters own` 26 times and `Handbook synthesis (bounded)` 31 times. The synthesis labels are required evidence boundaries and must remain at point of use, but the surrounding prose repeatedly follows the same generated cadence: definition, replenishment example, `The trade-off`, `Failure modes include`, security, cost, and `Later chapters own`. Twelve single-line paragraphs exceed 80 words; the densest reach 107 words at lines 133 and 388. The takeaways run to roughly 314 words, and six bullets repeat full synthesis qualifications and citations already established above. This conflicts with the brief's request for concise takeaways and the style contract's ban on repetitive wrap-ups.

**Concrete fix:** Preserve every required evidence label and source boundary, but consolidate later-chapter ownership into one forward-boundary paragraph at the end of each major H2. Split the 80-107-word paragraphs where evidence, decision consequence, and recovery implication change jobs. Vary subsection openings by leading with the concrete incident, decision, or artifact that distinguishes that subsection. Reduce the takeaway section to short decision rules and keep detailed source qualifications at their earlier point of proof or in one bounded note beneath the list.

#### I4. The ADR exercise requires a selection without supplying or explicitly delegating a cost envelope

**Locations:** `01-mlops-architecture-foundations.md:396-417`, especially constraints at `:398`, selection prompt at `:400`, required cost envelope at `:406`, and scoring at `:417`.

The exercise supplies timing, retention, recovery, residency, and exit constraints, then asks the learner to select a composition. It also requires a cost envelope, lifecycle cost evidence, and a firm decision, but no budget, staffing capacity beyond the vague phrase `limited capacity`, workload volume, provider quote, or instruction to define and sensitivity-test missing inputs is provided. A defensible architect can identify the missing decision evidence but cannot make a uniquely supportable selection from the stated facts. The scoring paragraph rewards a choice without explicitly rewarding refusal to invent decision inputs.

**Concrete fix:** Either add bounded illustrative staffing and cost constraints, or state that the learner must declare a provisional cost envelope and operating-capacity assumptions, identify unresolved inputs, and show which values would reverse the choice. Add an ADR answer skeleton or checklist tied to the 12 required fields, and make `records a decision blocker instead of inventing evidence` an observable strong-answer signal.

#### I5. One universal rubric cannot score all 18 questions consistently

**Locations:** Questions at `01-mlops-architecture-foundations.md:425-450`; universal instruction and rubric at `:452-460`; level calibration at `:462`; red flags at `:464`.

The questions are specific, but the rubric says to use the same five-level scale `for each answer`. Scores 4 and 5 require migration, provider exit, portfolio dependencies, jurisdiction, and enterprise evolution even when those dimensions are irrelevant to questions such as training-serving parity or mutable-alias rollback. Conversely, the rubric does not state the must-observe evidence for each question, so two interviewers can score the same answer differently while both claiming adherence. The level-calibration paragraph describes expected scope but does not map questions to applicable signals.

**Concrete fix:** Retain the five-level depth model, then add a compact question-to-evidence map. For each question, name two to four observable must-have signals, the relevant rubric dimensions, and one disqualifying omission. State that scope-irrelevant enterprise detail does not increase a score. Add interviewer guidance for follow-ups, partial answers, and when a Senior/Staff/Principal response should escalate rather than expand scope artificially.

### Minor

#### M1. Several wide tables lack a linear-access form

**Locations:** `EDITORIAL_STATUS.md:18-20` (nine columns for one data row), `GLOSSARY.md:7-22` (six dense columns), and Chapter 1 responsibility and sourcing tables at `:229-237` and `:285-290`.

The Markdown tables have header rows, but the status table provides no comparative benefit and becomes difficult to scan on narrow screens. The glossary and chapter tables contain long prose cells whose relationships are tedious in linear screen-reader navigation.

**Concrete fix:** Convert the single-row status table into a labeled vertical list. For the glossary and chapter tables, provide a concise lead-in that names the comparison keys and a linear equivalent or per-item definition-list form in the publication output. Preserve the two-column scoring rubric, which remains readable.

#### M2. Chapter 1 uses a bold date where other changelogs use an ATX date heading

**Location:** `01-mlops-architecture-foundations.md:511-515`.

The changelog date is `**2026-08-23**`, while maintained handbook files use `### 2026-08-23`. This is a small semantic-navigation inconsistency and conflicts with the workspace preference for ATX headings.

**Concrete fix:** Change the bold date to an H3 date heading without altering the changelog content.

#### M3. The README reading path names but does not link the evidence policy

**Location:** `mlops/architect-handbook/README.md:27`.

The architecture decision path links the style guide and diagram registry, then says `the evidence policy` as plain text even though the relevant section is available at `#evidence-and-publication-policy` in the same document.

**Concrete fix:** Link that phrase to `#evidence-and-publication-policy` so every step in the stated reading path is actionable.

## Positive editorial conclusions

- The chapter's information architecture follows the exact required section order and uses clear, descriptive H2/H3 labels.
- The voice is appropriately skeptical of vendor catalogues and unbounded claims, and the Senior/Staff/Principal distinction is based on decision horizon and organizational reach rather than inflated scale.
- The replenishment scenario is repeatedly identifiable as illustrative, and the production failure case clearly labels trigger, propagation, detection, containment, recovery, prevention, trade-offs, and operational close.
- Acronyms and controlled terms are expanded consistently; later-chapter references are plain-language boundaries rather than links to unwritten files.
- All 18 interview questions are present and meaningfully tiered. The five-level rubric contains observable language even though its per-question application needs correction.
- Citations use stable source keys and resolve to descriptive bibliography entries. No generic filler phrase from the banned list was found.
- Diagram alternatives accurately describe direction, ownership, blind detection paths, and non-authoritative views; the defect is association and navigation, not missing alternative content.

## Corroborating validation

```text
bash mlops/architect-handbook/scripts/test_validate_handbook.sh
PASS: all 27 validator tests passed; exit 0

bash mlops/architect-handbook/scripts/validate_handbook.sh --profile structure mlops/architect-handbook
PASS: structure validation completed with zero failures; exit 0

bash mlops/architect-handbook/scripts/validate_handbook.sh --profile release mlops/architect-handbook
PASS: release validation completed with zero failures; exit 0

Required banned-phrase and generated-fence scans
PASS: no maintained chapter/content defects

Link validation
PASS: all relative Markdown targets and checked anchors resolve
```

The Task 8 marker command also prints the ordinary verb `verify` in a research note and intentional validator fixtures under `scripts/`; these are not unresolved editorial markers. Automated validation does not test table-of-contents presence, point-of-use alternative-text association, prose cadence, exercise sufficiency, or question-level scoring reliability, so its pass does not close I1-I5.

## Approval gate

Do not approve the editorial review. Resolve I1-I5, rerun the 27-test suite and both validation profiles, repeat the link and content scans, and perform a focused editorial/accessibility rereview. M1-M3 should be corrected in the same pass but do not independently block rereview.

## Changelog

### 2026-08-23

- Completed the independent Task 8 editorial and accessibility review.
- Recorded zero Critical, five Important, and three Minor findings with exact locations and scoped fixes.
