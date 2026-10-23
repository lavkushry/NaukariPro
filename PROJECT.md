# Project: Autonomous Career Optimization Platform

## Architecture
The platform is designed to maximize candidate visibility (100k+ recruiter search appearances/month), capture live Resdex search demand, and drive automated high-precision job applications for an Azure Data Engineer profile (2.5 YOE).

### Core Components & Data Flow
1. **Profile & SEO Core (`naukri_system/config.json`, `NAUKRI_PROFILE_COMPLETE_UPDATE_DATA_ENGINEER.md`)**:
   - Single source of truth containing verified candidate facts (AGENTS.md Section 9).
   - Top 25 Azure Data Engineering industry keywords saturated across Headline, Skills, Summary, 4 Employment Roles, and 4 Lakehouse Projects.
   - All 17 experience and project bullets formatted strictly to the 5-stage engineering formula with zero forbidden verbs.
   - Strict 1-page ATS PDF generation engine (`AIResumeMaker`).
2. **Analytics & Performance Tracking Engine (`naukari_pro/modules/profile_performance.py`)**:
   - Extracts live recruiter search appearances, profile views, keyword hits, contact views, and resume downloads.
   - Paces against the 100k monthly search benchmark (daily pace ~3,333/day, projected 30-day velocity, % attainment).
   - Appends records to `Naukri_Live_Application_Tracker.xlsx` (`Recruiter_Performance_Log` and `Daily_Performance_Metrics`).
3. **Application & Sourcing Engine (`naukari_pro/modules/auto_apply.py`, `career_portals.py`, `multi_search.py`)**:
   - Slices Naukri 1-click apply feeds filtered by `calculate_match_score` threshold (>=70%).
   - Auto-fills screening questionnaires (experience, notice period, CTC, work auth) with confirmation verification.
   - External sourcing via Hacker News Who's Hiring and LinkedIn precision feeds.
   - Multi-portal form filler (Greenhouse, Ashby, Lever, Workday, Rippling) operating under review-only safety mode.
   - Structured `--dry-run` emitting validated `ApplicationPayload` objects without network dependencies or side-effects.
   - Logs company, title, URL, match score, and status to `Naukri_Live_Application_Tracker.xlsx` (`Applications_Log`).
4. **Cloud Daemon & Execution Resilience (`agy_schedule_runner.sh`, `systemd/`, `naukari_pro/session.py`)**:
   - Headless execution 3x daily (03:45, 09:00, 12:30 UTC / 09:15, 14:30, 18:00 IST).
   - Process-level mutual exclusion file lock (`flock`) preventing duplicate runs and Chromium singleton contention.
   - Cookie refresh, session persistence, and proxy support (`NAUKRI_PROXY`) for Akamai WAF mitigation.
   - Remote Linux cloud host (`ubuntu@141.148.195.233`) synchronization.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Top 25 Keyword Saturation | 100% saturation of Azure Data Engineering keywords across all candidate artifacts | M1 | Survey 1 (R1) |
| 2 | 17 Bullets 5-Stage Formula | All 9 employment and 8 project bullets comply with 5-stage formula and 0 forbidden verbs | M1 | Survey 1 (R1) |
| 3 | 1-Page ATS PDF Compilation | Single-page ATS-parseable PDF compiled without kerning splits or overflow | M1 | Survey 1 (R1) |
| 4 | Naukri Metadata Instructions | Comprehensive update guide with all 4 Lakehouse projects, correct title, and daily recency strategy | M1 | Survey 1 (R1) |
| 5 | ATS Keyword Map Modernization | Synchronize `04_ATS_KEYWORD_MAP.md` from legacy MLOps to Azure Data Engineering | M1 | Survey 1 (R1) |
| 6 | Application Tracker Schema Fix | Update `Naukri_Live_Application_Tracker.xlsx` with canonical 11 columns including `Match Score (%)` | M2 | Survey 2/3 (R3) |
| 7 | Application Logging Rectification | Update `log_to_excel()` and `log_portal_application()` to record `match_score` | M2 | Survey 2/3 (R3) |
| 8 | 100k Recruiter Benchmark Pacing | Implement daily pace (~3,333/day), projected 30-day velocity, and deficit metrics in `profile_performance.py` | M2 | Survey 3 (R3) |
| 9 | Performance Logging Persistence | Persist live recruiter metrics to JSON and `Naukri_Live_Application_Tracker.xlsx` | M2 | Survey 3 (R3) |
| 10 | Match Scoring Gate (>=70%) | Integrate `calculate_match_score` into `auto_apply.py` to filter out non-matching vacancies | M3 | Survey 2 (R2) |
| 11 | Structured Dry-Run Engine | Refactor `--dry-run` to output structured `ApplicationPayload` objects with offline capability | M3 | Survey 3 (R2) |
| 12 | Career Portal Dry-Run Support | Add dry-run support to `CareerPortalFiller` in `career_portals.py` | M3 | Survey 3 (R2) |
| 13 | Multi-Channel Sourcing Verification | Ensure HN Who's Hiring and LinkedIn feeds generate valid candidate payloads | M3 | Survey 2 (R2) |
| 14 | Schedule Collision Resolution | Remove redundant crontab entry so only systemd timer `naukaripro-agy.timer` triggers schedule | M4 | Survey 2 (R4) |
| 15 | Process-Level File Locking | Implement `flock` in `agy_schedule_runner.sh` and Python file lock to prevent Chromium singleton crashes | M4 | Survey 2 (R4) |
| 16 | Headless Cloud Proxy Routing | Wire `NAUKRI_PROXY` into Playwright `launch_persistent_context` to bypass cloud datacenter WAF blocks | M4 | Survey 2 (R4) |
| 17 | Remote VM Synchronization | Deploy and verify all fixes on remote Linux cloud host `ubuntu@141.148.195.233` | M4 | Survey 2 (R4) |
| 18 | Offline Regression Test Suite | Implement Tiers 1-4 test cases in `tests/test_offline_suite.py` passing 100% on macOS and Linux | M5 | Survey 3 (Verif) |
| 19 | Adversarial Coverage Hardening | Run Tier 5 adversarial stress testing and forensic audit for zero integrity violations | M5 | Project Pattern |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | SEO & Profile Ranking Optimization | Features 1, 2, 3, 4, 5 | None | DONE (148/148 tests pass, 100/100 ATS score, dual 1-page PDF verified) |
| M2 | Recruiter Search Analytics & Application Tracker | Features 6, 7, 8, 9 | M1 | DONE (166/166 tests pass, 11-col schema & rows 108-111 verified, 100k benchmark verified, 180 repeat-write stress clean) |
| M3 | Autonomous Multi-Channel Application Engine & Dry-Run | Features 10, 11, 12, 13 | M2 | DONE (Verified >=70% threshold gate, offline dry-run payload engine, career portal dry-run, HN/LinkedIn sourcing) |
| M4 | Resilient Cloud Daemon & Remote Infrastructure Security | Features 14, 15, 16, 17 | M3 | IN_PROGRESS |
| M5 | Final E2E Regression Suite & Adversarial Verification | Features 18, 19 | M1, M2, M3, M4, TEST_READY.md | PLANNED |

---

## Interface Contracts

### `naukari_pro/modules/job_alerts.py` ↔ `naukari_pro/modules/auto_apply.py`
```python
def calculate_match_score(text: str) -> int:
    """
    Computes weighted keyword match score (0-100) based on Azure Data Engineering competencies.
    Returns: integer score. Threshold >= 70 required to apply.
    """
```

### `naukari_pro/modules/auto_apply.py` ↔ `Naukri_Live_Application_Tracker.xlsx`
```python
def log_to_excel(
    title: str,
    company: str,
    status: str,
    match_score: int,
    app_type: str = "1-Click Apply",
    salary: str = "N/A",
    url: str = "N/A"
) -> bool:
    """
    Appends 11-column record to Applications_Log:
    [Application Date, Company Name, Job Title, Match Score (%), Role Category,
     Experience Required, Location, Application Type, Status, Job URL, Recruiter Response]
    """
```

### `naukari_pro/modules/profile_performance.py` ↔ 100k Benchmark Model
```python
@dataclass
class BenchmarkPacing:
    total_searches_30d: int
    target_monthly: int = 100000
    daily_target: float = 3333.33
    current_daily_pace: float
    projected_monthly: int
    percent_attainment: float
    status: str  # "ON_TRACK", "AHEAD", "DEFICIT"
```

### `--dry-run` Application Payload Contract
```python
@dataclass
class ApplicationPayload:
    company: str
    title: str
    url: str
    match_score: int
    salary: str
    answers: Dict[str, Any]
    dry_run: bool = True
    status: str = "VALIDATED_PAYLOAD"
```

---

## Code Layout
- `naukri_system/config.json`: Master candidate profile facts & technical competencies (Owned by M1)
- `04_ATS_KEYWORD_MAP.md`: Azure Data Engineering keyword taxonomy (Owned by M1)
- `NAUKRI_PROFILE_COMPLETE_UPDATE_DATA_ENGINEER.md`: Step-by-step Resdex SEO update guide (Owned by M1)
- `Azure_Data_Engineer_Resume.tex` / `.md`: LaTeX resume source & 1-page PDF (Owned by M1)
- `Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf`: Canonical 1-page ATS PDF (Owned by M1)
- `Naukri_Live_Application_Tracker.xlsx`: Master job application & performance workbook (Owned by M2)
- `naukari_pro/modules/profile_performance.py`: Recruiter metrics & 100k benchmark engine (Owned by M2)
- `naukari_pro/modules/auto_apply.py`: Multi-engine job discovery & 1-click apply (Owned by M2 & M3)
- `naukari_pro/modules/career_portals.py`: External portal form filler & tracker (Owned by M2 & M3)
- `naukari_pro/modules/multi_search.py`: HN & LinkedIn multi-channel sourcing (Owned by M3)
- `agy_schedule_runner.sh`: Cloud runner script with process lock (Owned by M4)
- `systemd/`: Systemd service and timer units (Owned by M4)
- `install_linux_schedule.sh`: Linux host deployment installer (Owned by M4)
- `naukari_pro/session.py`: Browser session & proxy configuration (Owned by M4)
- `tests/test_offline_suite.py`: Automated offline test suite covering Tiers 1-4 (Owned by E2E Testing Track)
