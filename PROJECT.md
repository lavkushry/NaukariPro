# Project: Autonomous Career Optimization Platform (Iteration 2: Live Conversion & 100k Search Fix)

## Architecture
The platform is an autonomous career optimization engine engineered to maximize live recruiter search appearances (targeting 100k+ monthly impressions on Naukri Resdex), capture high-intent recruiter demand, and execute automated high-precision job applications for an Azure Data Engineer profile (2.5 YOE).

### Core Components & Data Flow (Iteration 2)
1. **Live Profile & Resdex Persistence Core (`scripts/sync_naukri_live_profile.py`, `naukri_system/config.json`)**:
   - Manages authentic live Naukri profile state (`https://www.naukri.com/mnjuser/profile`).
   - Syncs 15-day notice period (highest conversion tier) and all 7 top Tier-1 tech hubs (`Bengaluru`, `Hyderabad`, `Pune`, `Gurugram`, `Noida`, `Mumbai`, `Chennai`).
   - Populates Key Skills tag cloud and Detailed IT Skills table (13 skills with versions and experience years).
   - Enforces full 247-char Azure Data Engineer headline saturation.
   - Eliminates once-per-day skip barriers across `profile_enhancer.py`, `sync_naukri_live_profile.py`, `pro_autopilot.py`, and `agy_schedule_runner.sh` to enable continuous 3x/day profile freshness boosting.
   - Validates live DOM persistence via automated read-back verification script (`scripts/verify_naukri_live_profile_dom.py`).

2. **High-Volume Application & Sourcing Engine (`naukari_pro/modules/auto_apply.py`)**:
   - Executes multi-page search result pagination (removing `items.slice(0, 10)` hard truncation).
   - Enforces freshness sorting (`&sortBy=date` / `&freshness=1`) across expanded Azure Data Engineering keywords and multiple locations.
   - Harvests Naukri Recommended Jobs (`https://www.naukri.com/mnjuser/recommendedjobs`) and Recruiter NVites/Inbox directly in headless Playwright cloud runs.
   - Solves multi-turn screening chatbots with affirmative semantic radio selection, dropdown selection (`<select>` and custom controls), checkboxes, and contextual text answers.
   - Eliminates false-positive "Already Applied" submissions, validating authentic DOM confirmation (`Applied`, `Thank you for your responses`, etc.).
   - Persists all submitted applications to canonical 11-column `Naukri_Live_Application_Tracker.xlsx`.

3. **Live Authenticated Analytics Extraction (`naukari_pro/modules/profile_performance.py`)**:
   - Extracts genuine live recruiter telemetry directly from `https://www.naukri.com/mnjuser/performance`:
     - 90-day search appearances (baseline 621)
     - 7-day search appearances (baseline 33, +31%)
     - Recruiter actions (baseline 21: 7 profile views, 4 contact views [North Star ⭐], 2 resume downloads, 12 NVites, 1 bookmark)
     - Recruiter search keywords (Kubernetes, AWS Cloud, Databricks, Pipeline, etc.)
   - Fixes `cli.py display_report` crash and removes headless execution bypass.
   - Logs real-time metrics alongside application tracker without offline mocks.

4. **Resilient Cloud Infrastructure & Remote Sync (`ubuntu@141.148.195.233`, `scripts/sync_remote_cloud.sh`)**:
   - Synchronizes codebase and tracking data between macOS workspace, GitHub (`origin/main`), and remote cloud host (`/home/ubuntu/Resume`).
   - Fixes hardcoded paths and row assertions to achieve 100% test pass on both macOS and remote Linux ARM64 VM.
   - Maintains systemd user timer `naukaripro-agy.timer` and `agy_schedule_runner.sh` with kernel `flock` mutual exclusion for automated 3x daily execution.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 15-Day Notice Period Sync | Configure Notice Period to `15 Days or less` / `Immediate` in config and automate in `#lazyEmployment` / `#lazyCareerProfile` | M1 | Survey 1 (R1) |
| 2 | 7 Tier-1 Preferred Locations Sync | Enable all 7 hubs (`Bengaluru`, `Hyderabad`, `Pune`, `Gurugram`, `Noida`, `Mumbai`, `Chennai`) in config and `#lazyCareerProfile` | M1 | Survey 1 (R1) |
| 3 | Key Skills Tag Cloud Sync | Automate population of top 25 industry keywords into `#lazyKeySkills` | M1 | Survey 1 (R1) |
| 4 | Detailed IT Skills Table Sync | Automate table of 13 IT skills with versions, years, and last used into `#lazyItSkills` | M1 | Survey 1 (R1) |
| 5 | Full 247-Char Headline Overwrite | Ensure complete Azure Data Engineer headline saturation in `bump_profile` rather than micro-toggling punctuation | M1 | Survey 1 (R1) |
| 6 | Once-Per-Day Skip Barrier Removal | Remove date-equality throttles in `profile_enhancer.py`, `sync_naukri_live_profile.py`, `pro_autopilot.py`, and `agy_schedule_runner.sh` for continuous 3x/day boost | M1 | Survey 1 (R1) |
| 7 | Live DOM Persistence Verification | Implement `scripts/verify_naukri_live_profile_dom.py` to read back and assert all fields on live Naukri DOM | M1 | Survey 1 (R1) |
| 8 | Freshness-Sorted Search URLs | Add `&sortBy=date` / `&freshness=1` to search queries across expanded keywords (`Kafka`, `Snowflake`, `ADF`, `Medallion`) and iterate all locations | M2 | Survey 2 (R2) |
| 9 | Multi-Page SRP Pagination | Remove `items.slice(0, 10)` hard-truncation; implement multi-page navigation to harvest all matching vacancies up to daily limit | M2 | Survey 2 (R2) |
| 10 | Recommended Jobs & NVites Harvesting | Add automated harvesting of `/mnjuser/recommendedjobs` and `/mnjuser/inbox` in `PlaywrightRunner.run_async()` at >=70% score | M2 | Survey 2 (R2) |
| 11 | Semantic Screening Chatbot Solver | Multi-turn solver with affirmative radio matching, dropdown `<select>` handling, checkbox selection, and contextual text answers | M2 | Survey 2 (R2) |
| 12 | Live DOM Confirmation & Bug Fix | Fix "Already Applied" false positive; confirm authentic application submission and log to canonical 11-column Excel tracker | M2 | Survey 2 (R2) |
| 13 | Authentic Performance Endpoint Fix | Update `profile_performance.py` from `/mnjuser/profile-performance` to `https://www.naukri.com/mnjuser/performance` | M3 | Survey 3 (R3) |
| 14 | Real Live Telemetry DOM Extraction | Extract genuine 90d/7d search appearances, recruiter actions, profile views, contact views, downloads, NVites, and keywords from live DOM | M3 | Survey 3 (R3) |
| 15 | CLI & Autopilot Analytics Wiring | Fix `cli.py` `AttributeError: display_report`, remove headless `page=None` bypass, and record live telemetry during autopilot runs | M3 | Survey 3 (R3) |
| 16 | Zero Offline Mocks for Live Metrics | Remove synthetic mock fallbacks in performance reporting; log real before/after metrics in Excel tracker | M3 | Survey 3 (R3) |
| 17 | Bidirectional Cloud Sync Tooling | Create `scripts/sync_remote_cloud.sh` to sync between local macOS, GitHub, and remote host `ubuntu@141.148.195.233` | M4 | Survey 3 (R4) |
| 18 | Test Suite Platform Portability | Fix hardcoded paths and row count assertions across all 11 test files for 100% pass on both macOS and Linux ARM64 | M4 | Survey 3 (R4) |
| 19 | Remote Live Execution Verification | Deploy fixes to remote VM and execute live end-to-end run confirming profile updates and live application harvesting | M4 | Survey 3 (R4) |
| 20 | Remote Systemd Health Verification | Verify `naukaripro-agy.timer` and `agy_schedule_runner.sh` execute 3x daily without errors or lock collisions | M4 | Survey 3 (R4) |
| 21 | Full Regression Test Verification | Run full test suite on macOS and Linux ARM64 VM (100% pass, 0 failures, 0 skips) | M5 | Acceptance Criteria |
| 22 | Live High-Throughput Application Run | Verify >= 5 live applications submitted in a single run meeting >=70% match score | M5 | Acceptance Criteria |
| 23 | Independent Forensic Victory Audit | Comprehensive integrity audit verifying authentic DOM persistence, genuine applications, and live telemetry | M5 | Acceptance Criteria |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Live Profile DOM Persistence & 3x/Day Boost | Features 1, 2, 3, 4, 5, 6, 7 | None | DONE (Passed unanimous Gate Review Round 2, 215/215 tests pass, CLEAN audit) |
| M2 | High-Volume Live Application & Recommended Jobs | Features 8, 9, 10, 11, 12 | M1 | DONE (Passed unanimous Gate Review Round 3, 213/213 tests pass, CLEAN audit) |
| M3 | Live Authenticated Naukri Analytics Extraction | Features 13, 14, 15, 16 | M1, M2 | IN_PROGRESS |
| M4 | End-to-End Remote Cloud Sync & Execution Proof | Features 17, 18, 19, 20 | M1, M2, M3 | PLANNED |
| M5 | Final Victory Verification & Forensic Audit | Features 21, 22, 23 | M1, M2, M3, M4 | PLANNED |

---

## Interface Contracts

### `scripts/sync_naukri_live_profile.py` ↔ Live Naukri DOM (`/mnjuser/profile`)
```python
def sync_full_naukri_profile(page: Page, config: dict = None, force: bool = False) -> bool:
    """
    Synchronizes full Azure Data Engineer profile facts to live Naukri DOM:
    1. Notice Period -> '15 Days or less' / 'Immediate'
    2. Preferred Locations -> Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai
    3. Key Skills -> Top 25 Azure Data Engineering keywords in #lazyKeySkills
    4. IT Skills -> 13 skills with versions, years, last used in #lazyItSkills
    5. Headline -> Full 247-char saturated headline
    6. Profile Summary & 4 Employment Roles & 4 Lakehouse Projects
    7. 1-Page ATS PDF Upload
    8. Freshness Boost (runs every execution without once-per-day skip)
    """

def verify_live_profile_dom(page: Page, config: dict = None) -> dict:
    """
    Reads back saved profile fields from live DOM at https://www.naukri.com/mnjuser/profile
    Returns verification dictionary asserting persistence of headline, summary, key skills,
    notice period, preferred locations, and uploaded resume filename.
    """
```

### `naukari_pro/modules/auto_apply.py` ↔ Naukri Job Search & Recommended Feeds
```python
async def harvest_and_apply_jobs(
    page: Page,
    keywords: list[str],
    locations: list[str],
    limit: int = 15,
    min_score: int = 70
) -> list[dict]:
    """
    1. Iterates multi-page SRP with &sortBy=date and &freshness=1
    2. Navigates to https://www.naukri.com/mnjuser/recommendedjobs
    3. Evaluates full JD match score (>=70%)
    4. Solves multi-turn screening chatbots (affirmative radios, dropdowns, checkboxes, contextual text)
    5. Validates authentic DOM confirmation (Applied, Thank you for your responses)
    6. Appends to canonical 11-column Naukri_Live_Application_Tracker.xlsx
    """
```

### `naukari_pro/modules/profile_performance.py` ↔ Live Naukri Analytics (`/mnjuser/performance`)
```python
def extract_live_naukri_performance(page: Page) -> dict:
    """
    Navigates to https://www.naukri.com/mnjuser/performance and extracts:
    - total_searches_90d: int (e.g. 621)
    - searches_7d: int (e.g. 33)
    - recruiter_actions: int (e.g. 21)
    - profile_views: int (e.g. 7)
    - contact_views: int (e.g. 4)
    - resume_downloads: int (e.g. 2)
    - nvites_received: int (e.g. 12)
    - search_keywords: list[tuple[str, int]]
    """
```

---

## Code Layout
- `naukri_system/config.json`: Master candidate profile ground truth (Notice Period 15 days, 7 Tier-1 locations, skills, summary).
- `scripts/sync_naukri_live_profile.py`: Playwright live profile sync automation and DOM persistence functions.
- `scripts/verify_naukri_live_profile_dom.py`: Independent live DOM read-back assertion script.
- `naukari_pro/modules/profile_enhancer.py`: Profile freshness bumper (3x/day boost logic, interval cooldown).
- `naukari_pro/modules/pro_autopilot.py`: Autonomous orchestrator for scheduled runs (profile boost + apply + analytics).
- `naukari_pro/modules/auto_apply.py`: Multi-page job search, recommended jobs harvester, chatbot solver, and live application execution.
- `naukari_pro/modules/profile_performance.py`: Authenticated live performance analytics extractor and 100k pacing model.
- `scripts/sync_remote_cloud.sh`: Bidirectional sync script for remote Linux VM (`ubuntu@141.148.195.233`).
- `agy_schedule_runner.sh`: Remote shell wrapper with `flock` execution.
- `tests/`: Automated regression and offline test suites.
