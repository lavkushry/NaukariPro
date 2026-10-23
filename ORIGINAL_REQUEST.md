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
