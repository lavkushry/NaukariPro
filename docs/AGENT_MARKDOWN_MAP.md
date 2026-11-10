# Agent Markdown Map

> Single index for every agent (Cursor, Claude Code, Codex, Antigravity, Muse, Grok Bot, Copilot).
> Load only what the task needs. Root [`AGENTS.md`](../AGENTS.md) stays the always-on policy.

## Load order (every session)

1. User request (wins on conflict)
2. [`AGENTS.md`](../AGENTS.md) — resume facts, ATS rules, candidate memory (§9)
3. [`CLAUDE.md`](../CLAUDE.md) — Claude Code / Cursor compatibility pointer
4. Task branch below — open only the matching markdown
5. Skills — invoke via `npx skills` / agent skill catalog when the branch needs them

## Skills (world-top packs pinned for this project)

| Source | Why it is here |
|:---|:---|
| `skills-lock.json` (repo root) | Pin of 213 leaderboard skills (Nov 2026) |
| `.agents/skills/` | Local project skill tree (**gitignored**; restore from lock, do not vendor) |
| `~/.agents/skills/` | Global install (same packs; works across repos) |

Restore after clone:

```bash
./scripts/setup_agent_skills.sh
# equivalent:
npx skills experimental_install
```

Browse / search: https://skills.sh/

### When to invoke which skill family

| Task branch | Prefer skills from |
|:---|:---|
| Resume / ATS / bullets | Workspace `AGENTS.md` first; then writing / review skills |
| NaukariPro Python / MCP / apply | `playbooks/AGENTS.md` + debugging / TDD / verification skills |
| React / Next / web UI | `vercel-labs/agent-skills`, `anthropics/skills` frontend-design |
| Azure / AKS / Foundry | `microsoft/azure-skills` |
| Prisma / Supabase / DB | `prisma/skills`, `supabase/agent-skills` |
| Video / motion | `heygen-com/hyperframes`, `remotion-dev/skills`, `emilkowalski/skills` |
| Process (design → ship) | `obra/superpowers` (brainstorm, TDD, debug, verify) |
| Skill discovery | `find-skills` (`vercel-labs/skills`) |

## Markdown by branch

### Resume content (facts stay grounded)

| Doc | Open when |
|:---|:---|
| [`01_FACT_MATRIX.md`](../01_FACT_MATRIX.md) | Verifying titles, dates, employers, metrics |
| [`02_CANDIDATE_POSITIONING.md`](../02_CANDIDATE_POSITIONING.md) | Positioning / narrative |
| [`03_MLOPS_GAP_ANALYSIS.md`](../03_MLOPS_GAP_ANALYSIS.md) | Skill gaps vs target JDs |
| [`04_ATS_KEYWORD_MAP.md`](../04_ATS_KEYWORD_MAP.md) | Keyword coverage |
| [`05_EXPERIENCE_REWRITE.md`](../05_EXPERIENCE_REWRITE.md) | Experience bullets |
| [`06_PROJECT_SELECTION.md`](../06_PROJECT_SELECTION.md) | Project portfolio picks |
| [`09_RESUME_LAYOUT_SPEC.md`](../09_RESUME_LAYOUT_SPEC.md) | Layout / one-page constraints |
| [`10_FINAL_RESUME.md`](../10_FINAL_RESUME.md) | Final resume source |
| [`MLOPS_2YOE_RESUME_BLUEPRINT.md`](../MLOPS_2YOE_RESUME_BLUEPRINT.md) | Blueprint / samples |
| [`How_to_Write_MLOps_Experience_Points.md`](../How_to_Write_MLOps_Experience_Points.md) | Experience bullet craft |
| [`How_to_Write_MLOps_Project_Points.md`](../How_to_Write_MLOps_Project_Points.md) | Project bullet craft |
| [`COMPLETE_RESUME_STRATEGY_MASTERBUNDLE.md`](../COMPLETE_RESUME_STRATEGY_MASTERBUNDLE.md) | Full strategy reference |

### NaukariPro product / automation

| Doc | Open when |
|:---|:---|
| [`README.md`](../README.md) | CLI, quick start, feature overview |
| [`PROJECT.md`](../PROJECT.md) | Product scope |
| [`SYSTEM_ARCHITECTURE_AND_INVENTORY.md`](../SYSTEM_ARCHITECTURE_AND_INVENTORY.md) | Architecture inventory |
| [`playbooks/AGENTS.md`](../playbooks/AGENTS.md) | Runtime-agnostic apply run contract |
| [`playbooks/GROKBOT.md`](../playbooks/GROKBOT.md) | Grok Bot tool map |
| [`playbooks/MUSE.md`](../playbooks/MUSE.md) | Muse tool map |
| [`playbooks/ANTIGRAVITY.md`](../playbooks/ANTIGRAVITY.md) | Antigravity tool map |
| [`docs/M0_SECRETS_HYGIENE.md`](M0_SECRETS_HYGIENE.md) | Secrets rules |
| [`docs/M1_AI_GATEWAY_REPORT.md`](M1_AI_GATEWAY_REPORT.md) | AI gateway |
| [`docs/M2_AGGREGATOR_REPORT.md`](M2_AGGREGATOR_REPORT.md) | Job aggregator |
| [`docs/M5_CAPTCHA_REPORT.md`](M5_CAPTCHA_REPORT.md) | Captcha handling |
| [`TEST_INFRA.md`](../TEST_INFRA.md) / [`TEST_READY.md`](../TEST_READY.md) | Test readiness |

### Agent entrypoints (thin pointers)

| File | Runtime |
|:---|:---|
| [`AGENTS.md`](../AGENTS.md) | Universal (Codex, Cursor, others) |
| [`CLAUDE.md`](../CLAUDE.md) | Claude Code / Cursor |
| [`GEMINI.md`](../GEMINI.md) | Gemini CLI / Antigravity-class |
| [`.github/copilot-instructions.md`](../.github/copilot-instructions.md) | GitHub Copilot |
| [`.cursor/rules/workspace.mdc`](../.cursor/rules/workspace.mdc) | Cursor always-on rule |

## Hard invariants (all agents)

- Never invent candidate facts, metrics, employers, or dates — `AGENTS.md` §9 is authoritative.
- NaukariPro apply path: dry-run until human approval (`playbooks/AGENTS.md`).
- Do not copy `AGENTS.md` into other docs; point to it.
- Skills supplement policy; they never override user request or `AGENTS.md`.

## Changelog

### November 8, 2026

- Created agent markdown map + skills pin index for multi-runtime project use.
