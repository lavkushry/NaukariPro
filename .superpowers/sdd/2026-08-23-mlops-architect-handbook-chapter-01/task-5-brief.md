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

