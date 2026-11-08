# Connector Fleet Repair Log — NaukariPro v2.1

**Date:** 2026-11-08  
**Doctrine:** Probe before code; one connector at a time; fixed only when telemetry says so.

## Phase 0 — Layer bisect

| Experiment | Result |
|------------|--------|
| Golden fixture `tests/fixtures/aggregation/greenhouse_gitlab_jobs.json` → normalize → dedupe → `AggregationStore` | **aggregator_ok** — 2/2 jobs inserted, titles present in DB |
| Conclusion | Core parse/normalize/dedupe/store path works. Live breakage is **connectors / empty-success semantics / registry / scheduler (F2–F8)**, not a black-box store bug. Proceed R1 telemetry + empty-success fail-closed in parallel with R2. |

Evidence: in-process bisect script (temp SQLite), 2026-11-08.

## Probe classification table

| Connector | Probe | HTTP/status | Failure class | Suspected cause |
|-----------|-------|-------------|-----------------|-----------------|
| Greenhouse (gitlab) | P1 | 200, `jobs`=248, `meta` present | **HEALTHY** | Public API OK |
| Lever (`lever`) | P2 | 200, `[]` | **F4** silent-empty | Wrong/empty company slug treated as success |
| Lever (`netflix`) | P2 alt | 404 Document not found | **F2** | Stale board token in csv/sources |
| Lever (`palantir`) | P2 fix | 200, 305 postings | **HEALTHY** | Registry updated to palantir/spotify |
| Ashby (`ashby`) | P3 | 200, `jobs`=73 | **HEALTHY** | Public API OK; `jobs:null` → board_missing |
| Workday (nvidia External) | P4 | 200, total=2000, 20 postings/page | **HEALTHY** | 10-page cap + Role-Scope detail budget |
| LinkedIn | P5 | 301→auth wall / no cards in curl | **F1** / posture | **LINKEDIN_LITE** default; FULL opt-in audit |
| Naukri | P6 | curl stream error / no session | **F1** | Challenge-stop → 24h disable; OTP stack for F1 only |

Probe artifacts: `evidence/probes/2026-11-08/{gh,lev,ash,wd,li_probe}.json|html`  
Live contract fixtures: `tests/fixtures/boards/*_live_2026-11-08.json`

## Dual-path note

If `ingest-jobs` is healthy but apply “sees nothing,” check `career_portals.fetch_live_ats_vacancies` (hardcoded boards) separately from aggregation SQLite.  
**Repair:** apply feeds prefer `AggregationStore` / `fetch_live_normalized` first.

## R1 — Aggregator + telemetry

- Tables: `board_health`, `drop_events`, `config_audit`, `cycle_log`
- Fail-closed empty success (`empty_board` drop + `fetch_err`, never `sources_ok`)
- Identity: `greenhouse:{id}`, `lever:{id}`, `ashby:{id}`, `workday:{tenant}:{site}:{jobRequisitionId}`
- Scheduler: `systemd/naukaripro-ingest.{service,timer}` Asia/Kolkata (not beast `pro`)
- Lockfile: `naukari_pro/aggregation/ingest_lock.py` (pid+timestamp, 30m stale clear)
- Golden E2E: `tests/test_connector_fleet_repair.py::test_golden_fixture_e2e_board_health_and_cycle`

## R2 — JSON boards

| Board | Live fixture | Contract | Registry |
|-------|--------------|----------|----------|
| Greenhouse | `greenhouse_live_2026-11-08.json` | green | gitlab/stripe/databricks/… |
| Lever | `lever_live_2026-11-08.json` (palantir) | green | palantir/spotify/brex (netflix removed) |
| Ashby | `ashby_live_2026-11-08.json` | green; null→board_missing | sentry/ramp/notion/postman |

## R3 — Workday

- ≥3 verified pairs: nvidia / salesforce / adobe (`config/boards.csv` + `sources.json`)
- Hard cap **10 pages × 20**; detail GET only for Role-Scope G1 passers; budget 60
- Relative `postedOn` → parse or null (never crash)
- Tests: page cap + identity + `parse_workday_posted_on`

## R4 — LinkedIn Lite + Naukri posture

- Default `LINKEDIN_LITE` (`browser_posture.py`); FULL only via `config_audit` row
- Challenge → `board_health.fetch_err++`, 24h self-disable, screenshot/cycle event
- Naukri: wired into `auto_apply` challenge paths; parse-minimum `<5` cards → F3 reason

## R5 — Discovery

- `verify_board_live`: requires `status_code==200` **and** `len(jobs)≥1` (max 4 retries)
- `verified_boards_total` KPI on tracking dashboard + `AggregationStore.registry_kpi()`
- Expanded India-relevant registry rows in `config/boards.csv`

## R6 — Gates G-1…G-6

| Gate | Criterion | Status |
|------|-----------|--------|
| G-1 | Bisect recorded in this log | **PASS** |
| G-2 | JSON boards healthy + contract fixtures | **PASS** (tests + fixtures) |
| G-3 | Workday ≥3 pairs + page/detail caps | **PASS** |
| G-4 | LITE default; FULL opt-in; challenge-stop | **PASS** |
| G-5 | Golden E2E + drop reasons + cycle logs | **PASS** |
| G-6 | `healthy_boards ≥ 4` at submit boot; KPI visible; dead-board alarm | **PASS** (enforced in `handle_governed_apply` + `gates.assert_submit_boot_healthy`) |

7-day observation scaffold: `naukari_pro/aggregation/observe.py` → `runtime/observe/observe_7d_*.json`.  
Submit unlock is **not** permanent until 7d multi-board digest is reviewed.

## Live ingest proof (2026-11-08)

Bounded cycle (`runtime/live_repair.db`, 4 sources):

| Board | fetch_ok | jobs_seen | jobs_new |
|-------|----------|-----------|----------|
| greenhouse:gitlab | 1 | 248 | 84 |
| lever:palantir | 1 | 305 | 29 |
| ashby:sentry | 1 | 39 | 26 |
| workday:nvidia… | 1 | 200 | 200 |

`healthy_boards=4`, `verified_boards_total=4`, gates G-1…G-6 **all_passed=true**.  
7d observe digest: `naukari_pro/runtime/observe/observe_7d_2026-11-08.json`.

## Changelog

### 2026-11-08 (R1–R6)

- Phase 0 bisect + P1–P6 classification recorded.
- board_health / drop_events / cycle_log / ingest lock / systemd ingest timer.
- GH→Lever→Ashby contracts + Ashby null fail-closed + Lever registry fix.
- Workday caps, Role-Scope detail, ≥3 verified pairs.
- LinkedIn Lite / Naukri challenge-stop posture.
- Discovery probe-before-trust + verified_boards_total KPI.
- Gates G-1…G-6 + submit boot gate + 7d observe scaffold.
- Live ingest proof: 339 inserted, 4/4 boards HEALTHY.
