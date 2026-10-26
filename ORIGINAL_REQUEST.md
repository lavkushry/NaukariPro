# Original User Request

## 2026-10-23T07:30:52Z

# Teamwork Project Prompt

> Requested team: Full multi-agent engineering & optimization team

Build and execute an autonomous career optimization platform to maximize candidate profile visibility (targeting 100k+ recruiter search appearances/month), capture live Resdex search demand, and drive automated high-precision job applications for an Azure Data Engineer profile (2.5 YOE).

Working directory: /Users/lavkushkumar/Desktop/Resume
Integrity mode: benchmark

## Requirements

### R1. Comprehensive Resdex Search SEO & Keyword Saturation
Maximize recruiter search match rate across all Naukri metadata fields (Headline, Key Skills, Detailed IT Skills, Profile Summary, 4 Employment Roles, and 4 Lakehouse Projects) targeting high-frequency boolean search strings for Azure Data Engineering, Databricks, PySpark, Delta Lake, ADF, Kafka, Medallion Architecture, and Cloud CI/CD.

### R2. Autonomous Multi-Channel Application & Sourcing Engine
Automate scheduled job discovery, matching, and application execution across Naukri 1-click apply, chatbot questionnaire screening, and external high-growth opportunities (LinkedIn, Hacker News Who's Hiring, early-access listings).

### R3. Recruiter Search Analytics & Visibility Tracking
Extract and track live recruiter search appearance metrics, profile views, keyword search hits, and resume downloads from the candidate dashboard to measure real-world performance against the 100k monthly search benchmark.

### R4. Resilient Cloud Execution & Infrastructure Security
Ensure headless execution, cookie refresh, browser singleton lock management, and network retry logic operate 100% autonomously without manual intervention or failure on the remote Linux cloud host (`ubuntu@141.148.195.233`).

## Acceptance Criteria

### SEO & Profile Ranking
- [ ] 100% alignment of candidate title, skills, and projects with top 25 Azure Data Engineering industry keywords.
- [ ] All 17 experience and project bullet points conform strictly to the 5-stage engineering formula with quantified metrics and zero forbidden verbs.
- [ ] ATS resume compiles to a strict 1-page PDF achieving 100/100 quality score and passes plain-text ATS parsing.
- [ ] Profile active recency continuously maintained as "Profile last updated - Today".

### Application & Pipeline Delivery
- [ ] Automated pipeline executes on schedule 3x daily via headless cloud daemon, submitting applications to all matching roles meeting threshold score (>=70%).
- [ ] Every job submission logs company, job title, job URL, match score, and status into `Naukri_Live_Application_Tracker.xlsx`.
- [ ] Clean graceful error recovery with zero browser deadlock or unhandled exception exits.

### Verification & Testing
- [ ] Automated regression test suite (`tests/test_offline_suite.py`) passes 100% of test cases on both local macOS and remote Linux VM.
- [ ] Dry-run mode (`--dry-run`) produces validated application payloads without side-effects.

## 2026-10-23T10:51:10Z

# Teamwork Project Prompt

> Requested team: Full multi-agent engineering & optimization team

Build and execute an autonomous career optimization platform to maximize candidate profile visibility (targeting 100k+ recruiter search appearances/month), capture live Resdex search demand, and drive automated high-precision job applications for an Azure Data Engineer profile (2.5 YOE).

Working directory: /Users/lavkushkumar/Desktop/Resume
Integrity mode: benchmark

## Prior Run Context (Resume from Milestone 3 Gate & Milestone 4)
A prior teamwork orchestrator run in `.agents/teamwork/teamwork_preview_orchestrator_1` completed:
- **Phase 0 Survey, `PROJECT.md`, and `TEST_INFRA.md`**: Completed.
- **Milestone 1 (R1: Comprehensive Resdex Search SEO & Keyword Saturation)**: Passed unanimous Gate Review & Forensic Audit (148/148 tests passing, 1-page ATS PDF verified in both LaTeX and ReportLab, 988-char Naukri summary bounds, all 17 bullets compliant with 5-stage engineering formula).
- **Milestone 2 (R3: Recruiter Search Analytics & Visibility Tracking)**: Passed unanimous Gate Review & Forensic Audit (166/166 tests passing, 11-column canonical `Naukri_Live_Application_Tracker.xlsx` verified across all rows, 100k monthly search benchmark pacing math in `profile_performance.py`).
- **Milestone 3 (R2: Autonomous Multi-Channel Application & Sourcing Engine)**: Worker M3 Iteration 2 was applying the remediation fixes for authentic `>=70%` match score threshold gating (no artificial 85% fallback), empty-JD title/tags evaluation, `AGENTS.md §9` employment history mapping, and `detect_ats(None)` null safety when the previous model hit a 429 quota limit.

Please inspect the current workspace state and `.agents/teamwork/teamwork_preview_orchestrator_1`, complete/verify Milestone 3 Iteration 2 gate clearance, execute Milestone 4 (R4: Resilient Cloud Execution & Infrastructure Security on `ubuntu@141.148.195.233` & local/remote sync), and complete the final Victory Audit.

## Requirements

### R1. Comprehensive Resdex Search SEO & Keyword Saturation
Maximize recruiter search match rate across all Naukri metadata fields (Headline, Key Skills, Detailed IT Skills, Profile Summary, 4 Employment Roles, and 4 Lakehouse Projects) targeting high-frequency boolean search strings for Azure Data Engineering, Databricks, PySpark, Delta Lake, ADF, Kafka, Medallion Architecture, and Cloud CI/CD.

### R2. Autonomous Multi-Channel Application & Sourcing Engine
Automate scheduled job discovery, matching, and application execution across Naukri 1-click apply, chatbot questionnaire screening, and external high-growth opportunities (LinkedIn, Hacker News Who's Hiring, early-access listings).

### R3. Recruiter Search Analytics & Visibility Tracking
Extract and track live recruiter search appearance metrics, profile views, keyword search hits, and resume downloads from the candidate dashboard to measure real-world performance against the 100k monthly search benchmark.

### R4. Resilient Cloud Execution & Infrastructure Security
Ensure headless execution, cookie refresh, browser singleton lock management, and network retry logic operate 100% autonomously without manual intervention or failure on the remote Linux cloud host (`ubuntu@141.148.195.233`).

## Acceptance Criteria

### SEO & Profile Ranking
- [ ] 100% alignment of candidate title, skills, and projects with top 25 Azure Data Engineering industry keywords.
- [ ] All 17 experience and project bullet points conform strictly to the 5-stage engineering formula with quantified metrics and zero forbidden verbs.
- [ ] ATS resume compiles to a strict 1-page PDF achieving 100/100 quality score and passes plain-text ATS parsing.
- [ ] Profile active recency continuously maintained as "Profile last updated - Today".

### Application & Pipeline Delivery
- [ ] Automated pipeline executes on schedule 3x daily via headless cloud daemon, submitting applications to all matching roles meeting threshold score (>=70%).
- [ ] Every job submission logs company, job title, job URL, match score, and status into `Naukri_Live_Application_Tracker.xlsx`.
- [ ] Clean graceful error recovery with zero browser deadlock or unhandled exception exits.

### Verification & Testing
- [ ] Automated regression test suite (`tests/test_offline_suite.py`) passes 100% of test cases on both local macOS and remote Linux VM.
- [ ] Dry-run mode (`--dry-run`) produces validated application payloads without side-effects.

## 2026-10-25T16:28:18Z

# Teamwork Project Prompt — Draft (Iteration 2: Live Conversion & 100k Search Fix)

> Status: Launched
> Goal: Launch full multi-agent teamwork system (Iteration 2)
> Requested team: Full multi-agent engineering & optimization team

Diagnose and fix all real-world bottlenecks preventing the candidate's live Naukri profile and autonomous cloud pipeline (`ubuntu@141.148.195.233`) from achieving 100k+ monthly recruiter search appearances and daily recruiter interview calls for Azure Data Engineer roles (2.5 YOE).

Working directory: /Users/lavkushkumar/Desktop/Resume
Integrity mode: development

## Requirements

### R1. Live Naukri Profile Audit, End-to-End Persistence & 3x/Day Active Boost
Audit the candidate's actual live authenticated Naukri profile (`naukri.com/mnjuser/profile`) via headless Playwright—not just offline JSON configs—and verify that all high-conversion Resdex fields are truly persisted live on Naukri:
- Live CV file uploaded (`Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf`)
- Notice Period set to highest recruiter conversion tier (`15 Days or less` / `Immediate`)
- All 7 top Tier-1 tech hubs enabled in Preferred Locations (`Bengaluru`, `Hyderabad`, `Pune`, `Gurugram`, `Noida`, `Mumbai`, `Chennai`)
- Resume Headline, Profile Summary, Key Skills, IT Skills (with experience years), 4 Employment Roles, and 4 Lakehouse Projects verified on the live DOM
- Continuous **every-run** profile freshness boost (removing once-per-day skip barriers so every morning, afternoon, and evening run refreshes live Resdex activity timestamp).

### R2. High-Volume, High-Precision Live Application & Recommended Job Harvesting
Fix low daily application volume by expanding live job discovery and submission across:
- Freshness-sorted (`freshness=1` / last 1–3 days) multi-page search queries across all core Azure Data Engineering, Databricks, PySpark, Delta Lake, ADF, Kafka, and Snowflake keywords
- Naukri Recommended Jobs (`/mnjuser/recommendedjobs`) and Recruiter NVites/Inbox opportunities
- Full-page JD evaluation (`>=70%` match threshold), automated multi-turn screening chatbot completion (handling text inputs, radio buttons, checkboxes, and dropdowns), and 1-click direct submissions.

### R3. Live Authenticated Naukri Analytics Extraction (No Offline Mocks)
Extract real-time search appearances, recruiter profile views, and recruiter actions directly from the authenticated Naukri dashboard/performance endpoints during live runs, logging real before/after telemetry alongside the 11-column `Naukri_Live_Application_Tracker.xlsx`.

### R4. End-to-End Remote Cloud Sync & Live Execution Proof
Deploy all fixes to `ubuntu@141.148.195.233:/home/ubuntu/Resume`, execute a live end-to-end verification run on the remote Linux server, and verify that live applications and live profile updates succeed with zero errors.

## Acceptance Criteria

### Live Profile & Resdex Conversion Verification (No Offline-Only Self-Certification)
- [ ] Live Playwright verification script reads back the authenticated Naukri profile DOM (`mnjuser/profile`) and confirms Headline, Summary, Key Skills, Notice Period, Preferred Locations, and uploaded Resume filename match the target Azure Data Engineer profile.
- [ ] Profile freshness bumper executes on every scheduled window (3x/day) rather than skipping after the first run of the day, verified by live timestamp updates.

### Live Job Application Throughput & Accuracy
- [ ] Live Playwright run harvests across both Search Results (with freshness filter & pagination) and Recommended Jobs, achieving >= 5 verified live job applications in a single verification run at >=70% match score.
- [ ] Screening chatbot solver handles text fields, radio options, checkboxes, and dropdowns on live Naukri job listings and confirms application submission via DOM state (`Applied` / `Thank you for your responses` / `saveApply`).
- [ ] All newly submitted applications are persisted to `Naukri_Live_Application_Tracker.xlsx` and synced between `ubuntu@141.148.195.233`, local macOS workspace, and GitHub (`origin/main`).

### Regression & Cloud Daemon Health
- [ ] All automated test suites (`pytest tests/test_*.py`) pass 100% on both local macOS and remote Linux (`ubuntu@141.148.195.233`).
- [ ] `naukaripro-agy.timer` and `agy_schedule_runner.sh` remain active and error-free on `ubuntu@141.148.195.233`.


## 2026-10-26T04:35:51Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Launch full multi-agent teamwork system for LinkedIn Automation
> Requested team: Full multi-agent engineering & optimization team

Build and deploy an enterprise-grade Autonomous LinkedIn Career & Easy Apply Engine for Lavkush Kumar (Azure Data Engineer, 2.5 YOE), incorporating battle-tested open-source heuristics from top GitHub LinkedIn bots (modal navigation, form filling, uncheck follow company, and stealth evasion) running seamlessly alongside NaukariPro on both local macOS and the Linux cloud server (`ubuntu@141.148.195.233`).

Working directory: /Users/lavkushkumar/Desktop/Resume
Integrity mode: development

## Requirements

### R1. LinkedIn Stealth Session & Cookie Architecture (`li_at`)
Implement an anti-detection Playwright session manager:
- Authenticated stealth session using `LINKEDIN_LI_AT` cookie injection from `.env` or `linkedin_system/session_cookies.json`.
- Fingerprint masking: random user-agents, realistic viewport, natural mouse/keystroke delays (30–80ms), and checkpoint/CAPTCHA detection with graceful fallback.
- CLI session diagnostic: `./naukariPro linkedin-verify` to validate session freshness and extract candidate identity without opening full browser windows.

### R2. High-Yield Precision Job Discovery Across 7 Tech Hubs & Remote
Automate multi-query LinkedIn job discovery:
- Generate freshness-sorted search targets (`f_TPR=r86400` / past 24h, `f_TPR=r604800` / past week) with Easy Apply filter (`f_AL=true`) and experience level (`f_E=2,3`).
- Search keywords: `Azure Data Engineer`, `Databricks`, `PySpark`, `Delta Lake`, `Azure Data Factory`, `Medallion Architecture`.
- Locations: Bengaluru, Hyderabad, Pune, Gurugram, Noida, Mumbai, Chennai, and Remote India.
- Strict Match Scoring Gate: Authentically evaluate vacancy details against `>=70%` match threshold before opening Easy Apply modal.

### R3. SOTA Multi-Step "Easy Apply" Bot (Open-Source Best Practices)
Implement an automated multi-step form filler inspired by the best GitHub Easy Apply bots:
- Step 1: Contact info (auto-fill Phone `+91-9122036484`, Email `lavkushry@gmail.com`).
- Step 2: Resume attachment (auto-upload `Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf` if requested or select latest).
- Step 3: Screening questionnaire solver (auto-solve common recruiter questions: years of experience with PySpark/Databricks/SQL/ADF, 15-day notice period, legally authorized to work, willing to relocate/commute, English proficiency).
- Step 4: Auto-uncheck "Follow company" checkbox before submission.
- Step 5: Submission confirmation & modal dismiss (detect "Application submitted", extract job ID, close dialog).
- Safety & throughput: Support high-volume target of up to 25–30 applications per cycle with rate-limit circuit breakers.

### R4. Unified Application Tracking, Regression Suite & Cloud Deployment
Integrate LinkedIn automation into the existing autonomous career daemon:
- Record every application into `Naukri_Live_Application_Tracker.xlsx` under a dedicated `LinkedIn_Applications_Log` worksheet (with fallback to `Applications_Log`).
- 100% offline dry-run mode (`--dry-run`) emitting validated payloads without network mutation.
- Comprehensive test suite (`tests/test_linkedin_suite.py`) covering session validation, search URL construction, questionnaire mapping, and payload logging.
- Integrated into `agy_schedule_runner.sh` for unattended 3x/day execution on `ubuntu@141.148.195.233`.

## Acceptance Criteria

### Session & Security
- [ ] Session loader authenticates cleanly via `LINKEDIN_LI_AT` cookie and detects expired or checkpointed states.
- [ ] Fingerprint stealth scripts prevent basic bot detection.

### Search & Matching
- [ ] Query generator constructs verified LinkedIn search URLs targeting all 7 tech hubs + Remote with `f_AL=true` and date filters.
- [ ] Match scoring engine gates applications at strict `>=70%` threshold; irrelevant or low-match roles are logged and skipped.

### Easy Apply Automation
- [ ] Multi-step Easy Apply bot autonomously completes multi-page modal dialogues (contact info, PDF resume, screening inputs, unchecking follow company) with DOM-verified submission.
- [ ] Successfully handles high-volume limit of up to 25–30 applications per cycle with safe delays.

### Tracking & Daemon Health
- [ ] Every applied role is recorded in `Naukri_Live_Application_Tracker.xlsx` with timestamp, company, title, URL, match score, and portal type.
- [ ] Complete offline test suite (`pytest tests/test_linkedin_suite.py`) passes 100%.
- [ ] Executable via `./naukariPro linkedin-apply` and integrated into `agy_schedule_runner.sh` on `ubuntu@141.148.195.233`.
