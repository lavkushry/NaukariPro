# Big Hammer Gap Matrix (pre-deepen audit)

**Date:** November 8, 2026  
**Baseline:** ~69 unique attack callables rotating across 420 IDs via `__mutNN` labels.

| Hammer | Required | Seed vectors | Unique attacks (approx) | Critical gaps |
|--------|----------|--------------|-------------------------|---------------|
| H1 input | 50 | 20 | ~15 | RTL/emoji distinct, 10MB exact, SSRF variants, float IDs, mixed encodings |
| H2 llm | 45 | 12 | ~12 | Truncated mid-token, 10k flood variants, budget ledger, deterministic fallback |
| H3 state | 40 | 5 | ~5 | Kill at SQLite write, mid-JSONL, mid-fill-before-confirm, WAL corrupt reopen |
| H4 concurrency | 30 | 4 | ~3 | Threaded token race, parallel ledger, scheduler overlap |
| H5 resource | 30 | 4 | ~4 | Disk-full audit, 100k jobs bound, PDF size, streaming stall |
| H6 time | 25 | 6 | ~6 | Decay 44/46/365, midnight IST, leap-day, future posting, frozen clock |
| H7 network | 35 | 4 | ~4 | Reset, stall, 429 lies, DNS, captive portal, gzip bomb, redirect loop, TLS |
| H8 form | 45 | 5 | ~5 | Dup IDs, iframe, maxlength/action rewrite, shadow DOM, select rename, captcha step |
| H9 identity | 25 | 4 | ~4 | Profile merge, stale dedupe, repost new ID, cross-board cooldown variants |
| H10 security | 40 | 6 | ~6 | XXE, zip-slip, HMAC timing/replay, template injection, dependency pin assert |
| H11 runtime | 30 | 4 | ~4 | Monkeypatch schedule, evidence dir deleted, notification dead, clipboard raise |
| H12 operator | 25 | 5 | ~4 | Malformed .env, lockfile, nonexistent outdir, version skew, dry-run typos |

**Fixtures present:** `H1-07_csv_formula.txt`, `H8-01_react_remount.json` (2). Target: one fixture per novel exploit class.

**Invariants:** I5/I6/I7/I9 partial; I1–I4/I8/I10 not enforced against temp ledger.

**Phase 2–4:** combo matrix absent; chaos = attack sampler; mutation = 4 DIY needles.

## Changelog

### November 8, 2026

- Initial deepen-in-place gap audit before catalog expansion.
- Gaps closed: distinct 420 catalog, I1–I10 checker, combos, chaos pipeline, 8 mutants, Phase-5 F1–F7 fix loop.
