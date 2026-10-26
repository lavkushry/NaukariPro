# Project: Autonomous LinkedIn Career & Easy Apply Engine

## Architecture
The LinkedIn Career & Easy Apply Engine is an enterprise-grade autonomous job application system engineered for Lavkush Kumar (Azure Data Engineer, 2.5 YOE). It incorporates battle-tested heuristics from top open-source LinkedIn bots (modal navigation, form filling, uncheck follow company, and stealth evasion) running seamlessly alongside NaukariPro on both local macOS and the Linux cloud server (`ubuntu@141.148.195.233`).

### Core Components & Data Flow
1. **Stealth Session & Cookie Manager (`naukari_pro/modules/linkedin_session.py`)**:
   - Manages authenticated Playwright browser sessions using `LINKEDIN_LI_AT` cookie injection from `.env` or `linkedin_system/session_cookies.json`.
   - Injects `STEALTH_JS` fingerprint masking (navigator.webdriver override, WebGL vendor/renderer spoofing, random user-agents, realistic viewport, process-level locking via `.linkedin_session.lock`).
   - Detects session expiration, security checkpoints (`/checkpoint/challenge`, `/uas/consumer-captcha`), and provides diagnostic CLI `./naukariPro linkedin-verify`.

2. **Precision Job Discovery & Match Scoring (`naukari_pro/modules/linkedin_search.py`)**:
   - Generates freshness-sorted search targets across 7 Tier-1 Indian tech hubs (`Bengaluru`, `Hyderabad`, `Pune`, `Gurugram`, `Noida`, `Mumbai`, `Chennai`) and `Remote India` with exact geoIds.
   - Enforces query filters: `f_AL=true` (Easy Apply), `f_TPR=r86400` / `r604800` (past 24h / past week), `f_E=2,3` (Entry/Associate), and `sortBy=DD`.
   - Iterates core Azure Data Engineering keywords (`Azure Data Engineer`, `Databricks`, `PySpark`, `Delta Lake`, `Azure Data Factory`, `Medallion Architecture`).
   - Parses job cards and applies strict `>=70%` match scoring against candidate profile before opening modals.

3. **SOTA Multi-Step Easy Apply Bot (`naukari_pro/modules/linkedin_bot.py`)**:
   - Implements automated multi-step form filler using ArtDeco DOM selectors.
   - Step 1: Contact info auto-fill (Phone `+91-9122036484`, Email `lavkushry@gmail.com`).
   - Step 2: Resume attachment (uploads `Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf` or selects latest).
   - Step 3: Screening questionnaire solver (regex fuzzy matching: PySpark/Databricks/SQL/ADF/Python experience years, 15-day notice period, work authorization in India, willing to relocate/commute, English proficiency).
   - Step 4: Auto-uncheck "Follow company" checkbox on review step before submission.
   - Step 5: Submission confirmation & modal dismiss (detect "Application submitted", extract job ID, close dialog).
   - Inline error detection (`artdeco-inline-feedback--error`) and auto-discard fallback for unhandled dialogues.
   - High-volume throughput target of 25–30 applications per cycle with rate-limit circuit breakers and randomized human typing delays (30–80ms).

4. **Unified Tracking, Dry-Run & Cloud Integration (`naukari_pro/modules/linkedin_apply.py`, `agy_schedule_runner.sh`)**:
   - Records every application into `Naukri_Live_Application_Tracker.xlsx` under dedicated `LinkedIn_Applications_Log` worksheet (10 columns, LinkedIn Blue `#0A66C2` header) with fallback to `Applications_Log`.
   - 100% offline dry-run mode (`--dry-run`) emitting validated payloads without network mutation.
   - CLI commands `./naukariPro linkedin-verify` and `./naukariPro linkedin-apply` in `naukari_pro/cli.py`.
   - Comprehensive test suite (`tests/test_linkedin_suite.py`) passing 100% offline.
   - Integrated into `agy_schedule_runner.sh` for unattended 3x/day execution on `ubuntu@141.148.195.233`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | `li_at` Cookie Auth | Inject `LINKEDIN_LI_AT` from `.env` or `linkedin_system/session_cookies.json` with `.linkedin.com` domain | M1 | R1, Survey 1/2 |
| 2 | Anti-Detection & Stealth | WebGL spoofing, random UA, realistic viewport, process-level locking (`.linkedin_session.lock`), humanized typing (30–80ms) | M1 | R1, Survey 1/2 |
| 3 | Checkpoint / Expiry Detection | Detect expired sessions or security challenges (`/checkpoint/challenge`, `input#captcha`) with graceful error handling | M1 | R1, Survey 1/2 |
| 4 | CLI Diagnostic (`linkedin-verify`) | `./naukariPro linkedin-verify` command to validate session freshness and print candidate identity | M1 | R1, Survey 1 |
| 5 | Multi-Hub Search URL Generator | Construct search URLs for 7 Tech Hubs + Remote with geoIds, `f_AL=true`, `f_TPR=r86400`, `f_E=2,3` | M2 | R2, Survey 2 |
| 6 | Keyword Query Strategy | Iteration across `Azure Data Engineer`, `Databricks`, `PySpark`, `Delta Lake`, `ADF`, `Medallion Architecture` | M2 | R2, Survey 2 |
| 7 | Job Card Parsing & Deduplication | Parse search result job cards (ID, title, company, location, snippet) and track applied IDs | M2 | R2, Survey 1/2 |
| 8 | Strict Match Scoring Gate (>=70%) | Score JD requirements against candidate facts with strict `>=70%` cutoff; skip low-match roles | M2 | R2, Survey 1/2 |
| 9 | Easy Apply Modal Navigator | Detect in-app Easy Apply button, handle `div.jobs-easy-apply-modal`, track multi-step progression | M3 | R3, Survey 2 |
| 10 | Contact Info Auto-Fill | Auto-populate Phone `+91-9122036484`, Country Code `India (+91)`, and Email `lavkushry@gmail.com` | M3 | R3, Survey 1/2 |
| 11 | Resume File Attachment | Auto-upload `Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf` or select existing resume card | M3 | R3, Survey 1/2 |
| 12 | Screening Questionnaire Solver | Fuzzy regex solver for numeric experience, notice period (15 days), work authorization, commute, English | M3 | R3, Survey 1/2 |
| 13 | Auto-Uncheck Follow Company | Locate and uncheck the "Follow company" checkbox on review step prior to submission | M3 | R3, Survey 2 |
| 14 | Submission Confirmation & Discard | Confirm authentic submission (`Application submitted`), extract job ID, auto-discard on unresolvable steps | M3 | R3, Survey 2 |
| 15 | Rate-Limit Circuit Breakers | Support high-volume target of 25–30 applications per cycle with randomized delays and circuit breakers | M3 | R3, Survey 2 |
| 16 | Dedicated Excel Tracker Sheet | Record applications in `Naukri_Live_Application_Tracker.xlsx` under `LinkedIn_Applications_Log` (with fallback) | M4 | R4, Survey 1/3 |
| 17 | Offline Dry-Run Mode (--dry-run) | Emits validated application payloads without network mutation or browser opening | M4 | R4, Survey 3 |
| 18 | CLI Runner (`linkedin-apply`) | `./naukariPro linkedin-apply` with `--headless`, `--dry-run`, `--limit`, `--keywords`, `--locations` | M4 | R4, Survey 1/3 |
| 19 | Comprehensive Offline Test Suite | `tests/test_linkedin_suite.py` with 100% deterministic passes across session, search, bot, tracker | M4 | R4, Survey 3 |
| 20 | Cloud Daemon Integration | Integrate `./naukariPro linkedin-apply` into `agy_schedule_runner.sh` for unattended 3x/day runs under `flock` | M4 | R4, Survey 3 |
| 21 | Remote Cloud Deployment & Sync | Deploy codebase and env vars to `ubuntu@141.148.195.233`, verifying test suite passes on remote host | M4 | R4, Survey 3 |
| 22 | Final Victory Verification | Verify end-to-end functionality, 100% test pass, clean forensic audit, and notify Sentinel | M4 | Acceptance Criteria |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | LinkedIn Stealth Session & Cookie Architecture | Features 1, 2, 3, 4 (`linkedin_session.py`, `linkedin-verify`) | None | DONE (Passed Iter 3 Gate: 49/49 tests, 2 Reviewers APPROVE, 2 Challengers APPROVE, Auditor CLEAN) |
| M2 | High-Yield Precision Job Discovery Across 7 Tech Hubs & Remote | Features 5, 6, 7, 8 (`linkedin_search.py`, match scoring >=70%) | M1 | IN_PROGRESS |
| M3 | SOTA Multi-Step "Easy Apply" Bot (Open-Source Heuristics) | Features 9, 10, 11, 12, 13, 14, 15 (`linkedin_bot.py`) | M1, M2 | PLANNED |
| M4 | Unified Tracking, Dry-Run, Regression Suite & Cloud Deployment | Features 16, 17, 18, 19, 20, 21, 22 (`linkedin_apply.py`, tracker, tests, cloud) | M1, M2, M3 | PLANNED |

---

## Interface Contracts

### `naukari_pro/modules/linkedin_session.py`
```python
class LinkedInSessionManager:
    def __init__(self, session_dir: str = "linkedin_system/browser_session", cookie_path: Optional[str] = None):
        ...
    def get_li_at_cookie(self) -> Optional[str]:
        """Reads LINKEDIN_LI_AT from environment or session_cookies.json."""
        ...
    async def create_stealth_context(self, p: Playwright, headless: bool = True) -> BrowserContext:
        """Launches Chromium with STEALTH_JS, realistic viewport, and injects li_at cookie."""
        ...
    async def verify_session(self, page: Page) -> Dict[str, Any]:
        """Navigates to /feed or /check/identity to verify session freshness, returns user profile or error."""
        ...
```

### `naukari_pro/modules/linkedin_search.py`
```python
class LinkedInSearchEngine:
    TECH_HUBS = {
        "Bengaluru": "105214831",
        "Hyderabad": "105556953",
        "Pune": "103503673",
        "Gurugram": "104113038",
        "Noida": "100450919",
        "Mumbai": "106155005",
        "Chennai": "105822989",
        "Remote": "102713980"
    }
    def build_search_url(self, keyword: str, location: str, freshness_sec: int = 86400, easy_apply_only: bool = True) -> str:
        ...
    def evaluate_match_score(self, job_title: str, job_description: str, candidate_skills: List[str]) -> float:
        """Returns match score between 0.0 and 100.0. Gates at >= 70.0%."""
        ...
    async def parse_job_cards(self, page: Page) -> List[Dict[str, Any]]:
        """Parses job cards from search results list."""
        ...
```

### `naukari_pro/modules/linkedin_bot.py`
```python
class LinkedInEasyApplyBot:
    def __init__(self, page: Page, candidate_info: Dict[str, Any], resume_path: str):
        ...
    async def apply_to_job(self, job_url: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Executes multi-step Easy Apply:
        1. Open modal
        2. Fill contact info (phone, email)
        3. Upload or select resume
        4. Solve screening questions via regex dictionary
        5. Uncheck follow company checkbox
        6. Review and submit (or mock submit in dry-run)
        7. Confirm and dismiss modal
        """
        ...
    def solve_question(self, question_text: str, input_type: str, options: Optional[List[str]] = None) -> Any:
        ...
```

### `naukari_pro/modules/linkedin_apply.py`
```python
class LinkedInApplyRunner:
    def __init__(self, headless: bool = True, dry_run: bool = False, limit: int = 15):
        ...
    async def run(self) -> Dict[str, Any]:
        """Main coordinator: initializes session, searches vacancies, evaluates score >=70%, applies, and logs to Excel tracker."""
        ...
    def log_application_to_excel(self, entry: Dict[str, Any], tracker_path: str = "Naukri_Live_Application_Tracker.xlsx") -> bool:
        """Logs entry to LinkedIn_Applications_Log worksheet (with fallback to Applications_Log)."""
        ...
```

---

## Code Layout
- `naukari_pro/modules/linkedin_session.py`: Session management, cookie loading, Playwright context initialization, stealth injection, session diagnostic verification.
- `naukari_pro/modules/linkedin_search.py`: Search URL generator, geoIds, card parser, match scoring engine (>=70%).
- `naukari_pro/modules/linkedin_bot.py`: Multi-step Easy Apply modal solver, contact info filler, resume uploader, questionnaire regex solver, follow company unchecker, submit & dismiss.
- `naukari_pro/modules/linkedin_apply.py`: High-level runner facade orchestrating session, search, bot, tracker logging, and dry-run mode.
- `naukari_pro/cli.py`: Subparsers for `linkedin-verify` and `linkedin-apply`.
- `tests/test_linkedin_suite.py`: 100% offline regression test suite.
- `agy_schedule_runner.sh`: Cloud runner script on remote VM.
