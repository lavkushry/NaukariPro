# NaukariPro × Muse

Follow [`playbooks/AGENTS.md`](AGENTS.md). Muse-class runtimes typically speak OpenAI-compatible or Mistral endpoints.

## Connect

1. Set `AI_GATEWAY_DEFAULT_PROVIDER=mistral` (or `compat` with `AI_PROVIDER_COMPAT_BASE_URL` pointing at Muse).
2. Keys: `AI_PROVIDER_MISTRAL_API_KEY` / compat keys in `.env`.
3. MCP: `python -m naukari_pro.mcp.server http 7432` — Muse automations can POST `/tools/<name>` or `/mcp`.

## Muse webhook hooks (optional)

Subscribe to outbound events when enabled (M6+): `job.found`, `resume.tailored`, `application.submitted`, `error.blocked`.

Until webhooks ship, poll `get_stats` / `get_tracker`.

## Tool flow for Muse agents

```
list_sources → search_jobs → score_job → tailor_resume → draft_answers → apply_job(dry_run=true) → [human] approve_submission
```

## Changelog

### November 5, 2026

- Initial Muse mapping (M1).
