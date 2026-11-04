# NaukariPro × Antigravity

Follow [`playbooks/AGENTS.md`](AGENTS.md). Antigravity should treat NaukariPro as an MCP tool provider + CLI.

## Connect

```bash
# stdio MCP
python -m naukari_pro.mcp.server

# or HTTP bridge (autoapplycv-style localhost)
python -m naukari_pro.mcp.server http 7432
```

CLI mirrors:

| MCP | CLI |
|-----|-----|
| search / ingest | `naukariPro ingest-jobs` |
| score | `naukariPro match-eval` |
| tailor | `naukariPro resume-gen` |
| apply dry-run | `naukariPro governed-apply` |
| gateway | `naukariPro llm-status` |
| mcp serve | `naukariPro mcp` |

## Antigravity run checklist

1. `get_stats` — confirm gateway mode + deterministic_only flag
2. Discover → gate → score (no live apply)
3. Dry-run fill only
4. Stop for human approval before any `--submit` / `dry_run=false`
5. After approval token: `approve_submission` then governed submit path

## Changelog

### November 5, 2026

- Initial Antigravity mapping (M1).
