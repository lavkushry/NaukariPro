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
rg -L '^## Changelog$' mlops/architect-handbook/*.md mlops/architect-handbook/diagrams/chapter-01/README.md mlops/architect-handbook/sources/references.md
```

Expected: every `test` exits 0, the CSV header exactly matches Step 3, and the final `rg -L` prints nothing.

- [ ] **Step 5: Record the task checkpoint**

Run `find mlops/architect-handbook -type f -print0 | sort -z | xargs -0 shasum -a 256` and save the output in the execution ledger for this plan. Do not create a Git commit.

---

