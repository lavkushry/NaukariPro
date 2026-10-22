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

