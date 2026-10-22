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

