# NaukariPro v2 — Agent Playbook (runtime-agnostic)

> Use this playbook from **any** AI runtime (Grok Bot, Muse, Antigravity, Claude Code, Cursor, Codex).
> Runtime-specific tool names: see sibling files `GROKBOT.md`, `MUSE.md`, `ANTIGRAVITY.md`, `CLAUDE.md` (NaukariPro section).
> Workspace skills + full markdown router: [`../docs/AGENT_MARKDOWN_MAP.md`](../docs/AGENT_MARKDOWN_MAP.md). Candidate facts still come from root [`../AGENTS.md`](../AGENTS.md).

## North star

Find relevant India (+ remote-for-India) jobs → grounded tailored resume → dry-run fill → **human approval** → submit → ledger. Never invent candidate facts.

## Run contract (ordered)

1. **Source** — `list_sources` → `search_jobs` / aggregator ingest
2. **Gate** — deterministic title/location gates; `score_job` (LLM only if budget allows)
3. **Tailor** — `tailor_resume` (grounding validator must pass; novelty ≤ 0.34)
4. **Draft** — `draft_answers` → independent vet; ASK_USER on missing evidence
5. **Dry-run** — `apply_job` with `dry_run=true` (default). Verify 4 fill layers when available
6. **Approve** — human issues token → `approve_submission`
7. **Submit** — only after approval; log-before-submit + screenshot
8. **Track** — `get_tracker` / `get_stats`

## Hard rules

- `dry_run=true` unless an unexpired approval token exists
- Grounded-answer rate = 100% (no fabrication)
- CAPTCHA / SSO / legal attestation → `NEEDS HUMAN` (never bypass)
- Company cooldown / lifetime max applications enforced
- Secrets only from `.env` — never commit keys
- Prefer public JSON APIs; honor robots.txt / TDM-Reservation
- When `paused_budget` or daily/monthly cap hit → deterministic-only (do not block search)

## MCP entry

```bash
python -m naukari_pro.mcp.server          # stdio JSON-RPC
python -m naukari_pro.mcp.server http 7432
```

Tools: `search_jobs`, `get_job`, `score_job`, `tailor_resume`, `draft_answers`, `apply_job`, `approve_submission`, `get_tracker`, `get_stats`, `list_sources`.

## Provider switch (zero app-code change)

Set `AI_GATEWAY_DEFAULT_PROVIDER` or edit `config/ai_gateway.yml` (`groq` | `openai` | `gemini` | `xai` | `anthropic` | `ollama` | …).

## Changelog

### November 8, 2026

- Linked shared skills/markdown map for multi-runtime project use.

### November 5, 2026

- Initial NaukariPro v2 agent playbook (M1).
