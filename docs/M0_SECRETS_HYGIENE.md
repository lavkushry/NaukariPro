# M0 — Secrets Hygiene

## Done in-tree

- `.env` remains gitignored; `.env.example` uses placeholders only (no real email).
- `portal_accounts.json.example` scrubbed.
- Tracked `naukri_system/config.json` no longer stores email/phone/linkedin/github.
- `naukari_pro/config.py` loads identity from `CANDIDATE_*` / `NAUKRI_EMAIL` env vars (no hardcoded fallback email).
- `.gitignore` expanded for DBs, LLM cache, session JSON, `config.local.json`.
- GitHub Actions offline pytest workflow added.

## Required on your machine (not automated)

1. Confirm local `.env` has `CANDIDATE_NAME`, `CANDIDATE_EMAIL`, `CANDIDATE_PHONE`, etc.
2. **Rotate** Naukri password, Gmail app password, and LinkedIn `li_at` if they were ever committed or shared.
3. History rewrite (only with your explicit approval — rewrites `main` and needs force-push):

```bash
# Review first
git log --all --full-history -- .env portal_accounts.json

# Optional: git filter-repo to purge known secret paths from history
# pip install git-filter-repo
# git filter-repo --invert-paths --path .env --path portal_accounts.json --force
```

Do **not** force-push until you have rotated credentials and confirmed backups.
