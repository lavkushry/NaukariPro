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

