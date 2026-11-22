# Candidate Selection Root-Cause Diagnosis & Ready-to-Use Profile Updates

> **Candidate:** Lavkush Kumar (`lav84095@gmail.com` | `+91-9122036484` | Bangalore, India)  
> **Target Positioning:** Platform, DevOps, MLOps & AI Infrastructure Engineer (~2.5 YOE)  
> **Canonical URLs:** [`https://www.linkedin.com/in/lavkushry/`](https://www.linkedin.com/in/lavkushry/) | [`https://github.com/lavkushry`](https://github.com/lavkushry)  
> **Governing Policy:** [`AGENTS.md`](../AGENTS.md) (§§2–4, §6, §9) & [`01_FACT_MATRIX.md`](../01_FACT_MATRIX.md)  
> **Updated:** November 22, 2026

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Part I — Five-Area Root-Cause Diagnosis (F1)](#part-i--five-area-root-cause-diagnosis-f1)
   - [1. Broken Candidate URLs (`lavkush-kumar` 404s) & Zero Clickable PDF Hyperlinks](#1-broken-candidate-urls-lavkush-kumar-404s--zero-clickable-pdf-hyperlinks)
   - [2. Resume Credibility, Persona Dissonance & AI-Flagged Metrics](#2-resume-credibility-persona-dissonance--ai-flagged-metrics)
   - [3. Naukri CTR Collapse (1.0%–1.21% CTR, 0 Calls) & Auth Freeze](#3-naukri-ctr-collapse-10121-ctr-0-calls--auth-freeze)
   - [4. LinkedIn Session Expiry (`0` Easy Applies), `.env:31` Syntax Error & Profile Drift](#4-linkedin-session-expiry-0-easy-applies-env31-syntax-error--profile-drift)
   - [5. Auto-Apply Seniority/0%-Score Leaks & `FALLBACK (CLICKED_NO_CONFIRMATION)` Infinite Drain](#5-auto-apply-seniority0-score-leaks--fallback-clicked_no_confirmation-infinite-drain)
3. [Part II — Ready-to-Use Naukri Profile Copy (F5)](#part-ii--ready-to-use-naukri-profile-copy-f5)
4. [Part III — Ready-to-Use LinkedIn Profile Copy (F5)](#part-iii--ready-to-use-linkedin-profile-copy-f5)
5. [Part IV — Required Interactive Authentication Checklist (Zero Bypasses)](#part-iv--required-interactive-authentication-checklist-zero-bypasses)
6. [Changelog](#changelog)

---

## Executive Summary

End-to-end forensic analysis of the local repository (`HEAD d28511e`), compiled PDF resumes, Naukri/LinkedIn telemetry, and production VM logs/databases (`ubuntu@130.210.19.226:/home/ubuntu/Resume`) identified **five compounding failure modes** preventing shortlists and interview calls:

1. **Dead 404 URLs & Unclickable PDFs:** Every application, outreach pitch, and PDF sent `linkedin.com/in/lavkush-kumar` and `github.com/lavkush-kumar` (404s) instead of verified `lavkushry` profiles, while ReportLab-generated PDFs contained **zero** clickable `/URI` link annotations.
2. **Severe Credibility & Persona Dissonance:** CGI India (`DevOps Engineer`, ~3–5 months tenure) was inflated to `"DevOps Engineer / Azure Data Engineer"` with fabricated Azure Lakehouse bullets, genuine `AegisAgent` and `vulcan` repos were replaced by unlinked/404 drafts, lab tools (`Triton`, `vLLM`) were claimed as skills, and tailored PDFs emitted `( – )` empty date strings.
3. **Naukri CTR Collapse & Auth Freeze:** Naukri search-to-view CTR collapsed to **1.0%–1.21%** (`0` real recruiter calls) after pivoting to synthetic Azure Data Engineer keywords, and headless profile updates froze on **2026-11-18 18:10** due to OTP/CAPTCHA walls starting **2026-11-19 09:19**.
4. **LinkedIn Session Expiry & `.env:31` Breakage:** LinkedIn automation produced **0 Easy Applies** (`ERR_TOO_MANY_REDIRECTS` / `EXPIRED`) alongside a `python-dotenv` parse error on `.env:31` (`LINKEDIN_JSESSIONID`).
5. **Auto-Apply Seniority/Score Leaks & Infinite Drain Timeout:** Out of **2,196** tracked DB rows, **1,422** had `match_score <= 30` (**474** non-rejected), senior/managerial roles (`Staff`, `Principal`, `Sr Mgr`) leaked through `role_guard.py`, and **61–111** `FALLBACK (CLICKED_NO_CONFIRMATION)` rows triggered repeated re-drains until systemd killed the worker at the **90-minute (`5400s`)** timeout.

---

## Part I — Five-Area Root-Cause Diagnosis (F1)

### Evidence Summary Matrix

| Area | Primary Failure | Concrete Repo / VM Evidence | Selection Impact |
|:---|:---|:---|:---|
| **1. URLs & PDF Links** | `lavkush-kumar` 404s; `0` `/URI` PDF links | `.env:39–40`, `~/.job-apply/profile.json`, `11_FINAL_RESUME.tex:67–68`, `career_portals.py` (19 sites), `resume_maker.py:301–305`, `outreach_tracker.json` (25 hits across 15 leads) | Recruiters & ATS verify dead links (`404`); PDFs fail click-through |
| **2. Resume Credibility** | CGI Lakehouse inflation, ghost/unlinked repos, `Triton`/`vLLM` risk, `( – )` dates | `config.json:9,171–253,553–565`, `candidate_profile.py:22`, `linkedin_optimizer.py:35,83,220–342`, `render.py:86`, `tailor.py:110–118` | Instant technical screen rejection & AI-spam metric flags |
| **3. Naukri CTR & Freeze** | 1.0%–1.21% CTR, `0` calls; OTP/CAPTCHA freeze | `config.json:287–294` (`642` app / `7` views), `profile_performance_history.json:171–205` (`746` / `9` / `3.2%`), VM `agy_run_2026-11-21_18-01-41.log:81–125` (`993` / `10` / `4.26%`, frozen since `2026-11-18 18:10`) | Invisible to DevOps/Platform searches; profile updates stalled since Nov 18 |
| **4. LinkedIn Expiry** | `EXPIRED` session (`0` applies), `.env:31` parse error | VM `agy_run_2026-11-21_18-01-41.log:6,178–195,705–706` (`ERR_TOO_MANY_REDIRECTS`, `python-dotenv` line 31), `linkedin_system/` Lakehouse drift | Zero LinkedIn Easy Apply throughput |
| **5. Auto-Apply Leaks** | Senior/0% leaks & `FALLBACK` infinite drain | VM `applied_jobs.db` (`2,196` rows, `1,422` `<=30%`, `id=7469,7450,7430,7391,7397`, `111` fallback rows), `agy_run_2026-11-21_18-01-41.log:49–50,521–1416` (`5400s` timeout) | Wasted daily quota on Staff/Sr-Mgr roles; worker hung re-draining |

---

### 1. Broken Candidate URLs (`lavkush-kumar` 404s) & Zero Clickable PDF Hyperlinks

* **Wrong Vanity Slug Everywhere:** Both `.env` (lines 39–40) and `~/.job-apply/profile.json` (lines 27, 29, 37), along with `11_FINAL_RESUME.tex:67–68,134,141`, `Azure_Data_Engineer_Resume.tex:59–60,123`, `candidate_profile.py:107–109`, `resume_maker.py:301–302`, `linkedin_optimizer.py:95,282`, `recruiter_outreach.py:50–51,114`, `screening_solver.py:287–288`, `career_portals.py` (19 fallback sites + missing `portfolioUrl` forwarding), and all 15 `PITCH_SENT` records in `outreach_tracker.json` (25 occurrences) emitted `linkedin.com/in/lavkush-kumar` and `github.com/lavkush-kumar` (HTTP 404) instead of `https://www.linkedin.com/in/lavkushry/` and `https://github.com/lavkushry`.
* **Silent Precedence Bug:** `candidate_profile.py:_env_override()` (lines 192–208) did not read `CANDIDATE_LINKEDIN`, `CANDIDATE_GITHUB`, or `CANDIDATE_PORTFOLIO`, allowing stale values in `~/.job-apply/profile.json` to overwrite fixes.
* **Zero Clickable PDF Hyperlinks:** `naukari_pro/modules/resume_maker.py:303–305` and `naukari_pro/resume_gen/render.py:52–59` rendered contact lines as plain ReportLab `Paragraph` text with zero `<link href="...">` tags. Inspecting the previously deployed `Lavkush_Kumar_Azure_Data_Engineer_Resume.pdf` (local & VM `sha256: 9b8ff86e...`) confirmed `page['/Annots'] == []` (zero clickable `/URI` annotations), while `11_FINAL_RESUME.pdf` / `main.pdf` still carried stale `mailto:lavkushry@gmail.com` instead of `lav84095@gmail.com`.

---

### 2. Resume Credibility, Persona Dissonance & AI-Flagged Metrics

* **Fabricated CGI Title & Lakehouse Workloads:** `naukri_system/config.json:9,171–180`, `candidate_profile.py:22`, `scripts/sync_naukri_live_profile.py:5,435–451`, `Azure_Data_Engineer_Resume.tex:85–89`, and `linkedin_optimizer.py:220–342` rewrote CGI India (`DevOps Engineer`, joined Jun 2026) into `"DevOps Engineer / Azure Data Engineer"` with fabricated Azure Databricks, ADLS Gen2, ADF, and Unity Catalog production bullets (`60%`/`40%`/`45%`). Live Naukri sync actively overwrote `#designationSugg` at CGI India to `"Azure Data Engineer"`.
* **Ghost / Unlinked Projects & Lab-Skill Overclaiming:** `config.json:212–253` and `sync_naukri_live_profile.py:472–498` replaced verified public repositories (`AegisAgent`, `vulcan`) with 4 unlinked synthetic projects, while `MLOPS_2YOE_RESUME_BLUEPRINT.md:476,481` referenced 404 ghost repos (`mlops-platform-automation`, `genai-observability-platform`). Simultaneously, `linkedin_optimizer.py:35,83,164–165`, `profile_updater.py:48–49`, and `config.json:553–565` claimed `Triton Inference Server` and `vLLM` (`LAB / CANDIDATE RISK` in `01_FACT_MATRIX.md:124–125`).
* **AI-Flagged Percentages & Screening Inflation:** `screening_solver.py:188–245` answered `"2.5"` or `"2.0"` years for `Databricks`, `PySpark`, `Delta Lake`, `Azure Synapse`, `Microsoft Fabric`, `dbt`, `Unity Catalog`, and `Snowflake` despite total career tenure being ~2.5 years across DevOps/Platform/Security/Frontend roles (`01_FACT_MATRIX.md §1`). Combined with extreme metric stacking (`93%`, `83%`, `98%`, `94%`, `99.2%`), profiles failed both automated consistency checks and technical screening.
* **Empty Date Bug & LaTeX Kerning Splits:** `naukari_pro/resume_gen/tailor.py:110–118` dropped `dates`/`duration` while setting `start=None, end=None`, causing `naukari_pro/resume_gen/render.py:86` to print `( – )` in tailored PDFs (`Lavkush_Kumar_Azure_Data_Engineer_Target.pdf`). Meanwhile, `11_FINAL_RESUME.tex` used `[T1]{fontenc}` + `\ifpdftex` under `tectonic` (XeTeX), producing `SUMMAR Y`, `T erraform`, and `R TO` text-extraction splits.

---

### 3. Naukri CTR Collapse (1.0%–1.21% CTR, 0 Calls) & Auth Freeze

* **CTR Collapse Post-Pivot:**
  * `naukri_system/profile_performance_history.json:8–24` (Oct 23–25, 2026) shows incoming recruiter searches matched DevOps/Platform terms (`kubernetes`, `terraform`, `ansible`, `docker`, `jenkins`, `prometheus`, `grafana`, `argocd`).
  * After pivoting headline/summary/skills to synthetic Azure Data Engineer keywords (`Oct 28 – Nov 04, 2026`, `config.json:280–294`), 7-day baseline dropped to **642 search appearances**, **7 profile views (1.09% CTR)**, and **0 real calls**.
  * `profile_performance_history.json:171–205` (`2026-11-03 22:24`) recorded **746 appearances**, **9 views (1.21% CTR)**, **2 resume downloads**, and **3.2% goal attainment (`DEFICIT`)**.
  * Live VM telemetry (`logs/agy_run_2026-11-21_18-01-41.log:81–125`) recorded **993 search appearances**, **10 profile views (1.0% CTR)**, and **4.26% attainment (`DEFICIT`)**.
* **Headless Auth Freeze Since Nov 18–19:** VM `logs/agy_run_2026-11-21_18-01-41.log` confirms Naukri headless mutations froze after **2026-11-18 18:10** (`profile_mutations` last succeeded at **2026-11-18 12:40:22**) when Naukri enforced `HEADLESS AUTHENTICATION REQUIRED` (OTP / CAPTCHA challenge) starting **2026-11-19 09:19:42**.

---

### 4. LinkedIn Session Expiry (`0` Easy Applies), `.env:31` Syntax Error & Profile Drift

* **Expired Session & Zero Throughput:** VM log `logs/agy_run_2026-11-21_18-01-41.log:178–195,705–706` shows LinkedIn automation failing immediately with `ERR_TOO_MANY_REDIRECTS` and `Session verification failed: EXPIRED`, resulting in **0 LinkedIn Easy Applies**.
* **`.env:31` Parsing Error:** `logs/agy_run_2026-11-21_18-01-41.log:6` logs `python-dotenv could not parse statement starting at line 31` caused by unescaped embedded quotes (`4` quote chars in `LINKEDIN_JSESSIONID`), preventing clean cookie loading.
* **LinkedIn Profile Drift:** Legacy helper scripts (`linkedin_system/update_project_lakehouse.py`, `add_streaming_project.py`) and `linkedin_optimizer.py:220–406` pushed synthetic Azure DE titles/summaries/projects onto LinkedIn that contradicted the candidate's actual GitHub and CGI/HFCL employment history.

---

### 5. Auto-Apply Seniority/0%-Score Leaks & `FALLBACK (CLICKED_NO_CONFIRMATION)` Infinite Drain

* **Massive Seniority & Low-Score Leakage:** Querying VM `applied_jobs.db` (`2,196` total rows) showed **1,422 rows** with `match_score <= 30` (**474** non-rejected), because `role_guard.py` exempted target keywords from `score <= 0.0` checks and `auto_apply.py` ran a `Universal Apply queue (No Filtering)` (`agy_run_2026-11-21_18-01-41.log:49–50`). Specific leaked rows in `applied_jobs.db`:
  * `id=7469`: `Staff DevOps Engineer` (`5%` match)
  * `id=7450`: `Staff Site Reliability Engineer` (`10%` match)
  * `id=7448`, `id=7449`: `Staff Software Engineer` (`35%` match)
  * `id=7430`: `Senior DevOps Engineer` (`0%` match)
  * `id=7396`: `Staff SRE` (`20%` match)
  * `id=7391`: `Principal Databricks Engineer` (`45%` match)
  * `id=7393`: `Technical Data Engineering Manager` (`10%` match)
  * `id=7344`: `Data Engineer Manager` (`0%` match)
  * `id=7397`: `Sr Manager - Data Engineering` (`0%` match)
* **`FALLBACK (CLICKED_NO_CONFIRMATION)` Miscounting & 90-Minute Timeout:** `applied_jobs.db` contained **111** `FALLBACK (CLICKED_NO_CONFIRMATION)` rows. `career_portals.py:10023` incremented `submitted += 1` and `scorecard.py:153` counted unconfirmed fallbacks as `applied`, while `autonomous_loop.py` re-queued **61** `CLICKED_NO_CONFIRMATION` rows every cycle (`agy_run_2026-11-21_18-01-41.log:521–1416`, including Workday Adobe `Sr-Mgr--Software-Development_R172115-1`) until systemd terminated the worker at the **90-minute (`5400s`)** timeout.

---

## Part II — Ready-to-Use Naukri Profile Copy (F5)

### 1. Resume PDF Attachment
* Upload **`Lavkush_Kumar_MLOps_Resume.pdf`** (strictly 1 A4 page, single-column, clickable `/URI`s for LinkedIn, GitHub, `AegisAgent`, `vulcan`, and `Azure-Data-Engineering-Medallion-Lakehouse-Project`).

### 2. Resume Headline (`233 / 250` characters max)
```text
Platform & MLOps Engineer | Kubernetes (kubeadm, EKS) · Docker · Helm · Terraform · Ansible · ArgoCD · CI/CD · Prometheus · ELK · Kafka · Python · Rust | 2.5 YOE AI & Cloud Infrastructure | AZ-900 · CKA (In Progress) | 15 Days Notice
```

### 3. Profile Summary (`920 / 1000` characters max)
```text
Platform, DevOps & MLOps Engineer with ~2.5 years of experience building and operating high-availability Kubernetes platforms, IaC automation, CI/CD pipelines, and stateful data backbones. At CGI India, standardized multi-tenant AWS EKS infrastructure with Terraform/Ansible, Jenkins/GitLab CI + Trivy security gates, Nginx/Kong gateways, and ArgoCD/Helm GitOps. At HFCL Limited, automated 50-node bare-metal kubeadm Kubernetes clusters via 40+ Ansible roles (cutting bootstrap 2 days -> 4 hours, 83%), managed Kafka/Redis/PostgreSQL/TimescaleDB/MongoDB StatefulSets with Velero DR (RTO 8h -> 30min, 93%; MTTR -45%; 99.95% availability), and doubled Jenkins release frequency (2x). Built open-source AI/data projects: AegisAgent (Rust/Cedar/K8s <75ms policy eval), Project Vulcan (FastAPI/pgvector/Redis Redlock), and Azure Medallion Lakehouse (PySpark/Databricks/ADF). AZ-900, SC-200, CKA (In Progress). 15 days notice.
```

### 4. Key Skills (25 Grounded Tags)
`Kubernetes`, `Docker`, `Helm`, `Terraform`, `Ansible`, `AWS EKS`, `ArgoCD`, `CI/CD`, `Jenkins`, `GitLab CI`, `GitHub Actions`, `Trivy`, `Prometheus`, `Grafana`, `ELK Stack`, `Apache Kafka`, `Redis`, `PostgreSQL`, `TimescaleDB`, `MongoDB`, `Velero`, `Python`, `FastAPI`, `Rust`, `Linux`

### 5. IT Skills (Calibrated to `01_FACT_MATRIX.md`, `<= 2y 6m`)

| Skill | Version | Last Used | Experience |
|:---|:---|:---|:---|
| Python | 3.11+ | 2026 | 2 Years 6 Months |
| Linux & Bash | Ubuntu / RHEL | 2026 | 2 Years 6 Months |
| CI/CD (Jenkins, GitLab CI, GitHub Actions) | Enterprise | 2026 | 2 Years 0 Months |
| Docker & containerd | Latest | 2026 | 2 Years 0 Months |
| Kubernetes (kubeadm, AWS EKS) | 1.30+ | 2026 | 1 Year 6 Months |
| Terraform & Ansible | 1.8+ / 2.16+ | 2026 | 1 Year 6 Months |
| Prometheus, Grafana & ELK Stack | Latest | 2026 | 1 Year 6 Months |
| Apache Kafka, Redis & PostgreSQL/TimescaleDB | 3.x / 7.x / 16 | 2026 | 1 Year 0 Months |
| Helm & ArgoCD (GitOps) | v3 / 2.x | 2026 | 1 Year 0 Months |
| PySpark, Azure Databricks & Delta Lake (Projects) | 3.5+ | 2026 | 0 Years 6 Months |

### 6. Employment History (4 Canonical Entries — `AGENTS.md §9`)

1. **DevOps Engineer** | **CGI India** | `Jun 2026 – Present` | Bangalore, India | Notice: `15 Days or less`
   * Standardized multi-tenant AWS EKS container platform deployments using modular Terraform and Ansible, establishing reproducible cluster baselines, auto-scaling node groups, and IAM roles across 3 environments.
   * Engineered automated CI/CD pipelines in Jenkins and GitLab CI with Trivy vulnerability scanning, container linting, and staging smoke tests, eliminating manual release gates.
   * Hardened cluster ingress and API gateway policies using Nginx Ingress and Kong Gateway (rate-limiting, TLS termination), and automated GitOps rollouts with ArgoCD and Helm charts.
2. **Engineer 1 — DevOps / Platform Engineering** | **HFCL Limited** | `Aug 2025 – Jun 2026` | Bangalore, India
   * Automated bare-metal Kubernetes (`kubeadm`) cluster lifecycle via 40+ Ansible roles and Jinja2 templates (OS hardening, CNI, Harbor, Helm), cutting cluster bootstrap time from 2 days to 4 hours (83% reduction).
   * Operated a 50-node on-premise Kubernetes platform for 15+ distributed microservices with namespace isolation, RBAC, and HPA, sustaining 99.95% platform availability.
   * Orchestrated stateful distributed data backbones (Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB) on Kubernetes via StatefulSets; configured Velero DR and Prometheus/Grafana alerts, slashing RTO from 8h to 30min (93%) and MTTR by 45%.
   * Standardized declarative Jenkins pipelines with Docker, Helm, SonarQube, and Trivy security gates, enabling zero-downtime rolling updates and doubling release frequency (2x).
3. **Security Analyst Apprentice** | **CGI India** | `Sep 2024 – Aug 2025` | Bangalore, India
   * Centralized multi-source log ingestion via the ELK Stack (Elasticsearch, Logstash, Kibana), building operational dashboards and query filters that reduced root-cause investigation time by 35%.
   * Authored custom Logstash Grok patterns to parse high-volume unstructured syslog and firewall/IDS telemetry into structured schemas, cutting log triage time by 45%.
4. **Full Stack Developer Intern** | **Stipe Solutions** | `Mar 2024 – Sep 2024` | Bangalore, India
   * Developed 30+ cross-platform mobile screens using React Native and Flutter with RESTful API integrations and PostgreSQL query optimization for 1,000+ daily active users.

### 7. Projects (3 Verified Public Repositories)

1. **AegisAgent — Zero-Trust AI Agent Security Gateway** | `https://github.com/lavkushry/AegisAgent` (`2026`)
   * Architected an open-source zero-trust security gateway for AI agents in Rust, integrating the Cedar Policy Engine to enforce ABAC over MCP tool invocations with sub-75ms policy evaluation.
   * Engineered production Kubernetes Helm charts (`aegis-gateway`), ServiceMonitors, and NetworkPolicies with reproducible GitHub Actions CI/SAST pipelines ensuring 100% scan coverage.
2. **Project Vulcan — Enterprise Automation Control Plane** | `https://github.com/lavkushry/vulcan` (`2025`)
   * Architected an infrastructure automation control plane in Python (FastAPI) with Redis Redlock distributed locking and MinIO S3 decoupled storage to eliminate runbook race conditions.
   * Integrated semantic incident retrieval using PostgreSQL with pgvector (HNSW indexing) and WebSocket live log streaming, cutting SRE diagnostics under 2 minutes per task.
3. **Azure Medallion Lakehouse Platform** | `https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project` (`2026`)
   * Built an end-to-end Medallion Lakehouse (Bronze/Silver/Gold) on Azure Databricks, Delta Lake, and ADF, optimizing PySpark batch transformations to cut ETL runtime by 35% with ACID schema validation.

---

## Part III — Ready-to-Use LinkedIn Profile Copy (F5)

### 1. Contact & Vanity URL
* **LinkedIn URL:** `https://www.linkedin.com/in/lavkushry/`
* **GitHub:** `https://github.com/lavkushry`
* **Email:** `lav84095@gmail.com`
* **Location:** `Bengaluru, Karnataka, India`

### 2. LinkedIn Headline (`175 / 220` characters max)
```text
Platform & MLOps Engineer | Kubernetes (EKS, kubeadm) · Terraform · Ansible · ArgoCD · Docker · Helm · CI/CD · Kafka · Prometheus · Python · Rust | AI Infrastructure | 2.5 YOE
```

### 3. Open-to-Work Settings (`Recruiters only`)
* **Target Job Titles (5):** `MLOps Engineer`, `ML Platform Engineer`, `AI Infrastructure Engineer`, `DevOps Engineer`, `Platform Engineer`
* **Location Types:** `On-site`, `Hybrid`, `Remote`
* **Locations:** `Bengaluru`, `Hyderabad`, `Pune`, `Gurugram`, `Noida`, `Remote (India)`
* **Start Date:** `Immediately, I am actively applying` (Notice: 15 Days or less)

### 4. LinkedIn About Section (`1,964 / 2,600` characters max)
```text
Platform, DevOps & MLOps Infrastructure Engineer with ~2.5 years of experience building and automating high-availability Kubernetes platforms, stateful data backbones, and production CI/CD pipelines.

What I build and operate in production:
• Kubernetes & Cloud Platform Infrastructure: Multi-tenant AWS EKS cluster provisioning via modular Terraform and Ansible (CGI India), and 50-node bare-metal kubeadm cluster lifecycle automation across 40+ Ansible roles (HFCL Limited), cutting cluster bootstrap from 2 days to 4 hours (83% reduction) while sustaining 99.95% availability.
• Stateful Data Backbones & SRE: Operated Apache Kafka, Redis, PostgreSQL, TimescaleDB, and MongoDB StatefulSets on Kubernetes with Velero disaster recovery and Prometheus/Grafana observability — cutting RTO from 8 hours to 30 minutes (93% reduction) and MTTR by 45%.
• CI/CD, GitOps & Security: Automated declarative Jenkins, GitLab CI, and GitHub Actions pipelines with Trivy vulnerability scanning, SonarQube, Nginx/Kong ingress policies, and ArgoCD/Helm GitOps rollouts (2x release frequency).
• Log Analytics & Telemetry: Centralized ELK Stack ingestion and custom Logstash Grok parsing for security/operational telemetry (CGI India), cutting root-cause investigation time by 35% and log triage time by 45%.

Open-Source AI Infrastructure & Data Platform Projects:
• AegisAgent (https://github.com/lavkushry/AegisAgent): Zero-trust AI agent security gateway in Rust with Cedar ABAC policy evaluation (<75ms latency) and Kubernetes Helm charts.
• Project Vulcan (https://github.com/lavkushry/vulcan): FastAPI automation control plane with Redis Redlock, MinIO S3, and PostgreSQL/pgvector HNSW retrieval (<2 min diagnostics).
• Azure Medallion Lakehouse (https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project): PySpark, Azure Databricks, Delta Lake, and ADF batch ETL platform (35% runtime cut).

Contact: lav84095@gmail.com | https://github.com/lavkushry
```

### 5. Experience (4 Canonical Entries)
Use the exact 4 roles, companies, dates (`Jun 2026 – Present`, `Aug 2025 – Jun 2026`, `Sep 2024 – Aug 2025`, `Mar 2024 – Sep 2024`), and grounded bullets listed in **Part II §6** above.

### 6. Projects (3 Verified Public Repos)
Use the exact 3 projects and verified `https://github.com/lavkushry/...` URLs listed in **Part II §7** above.

### 7. Top 50 Skills (Grounded in `01_FACT_MATRIX.md`)
1. Kubernetes, 2. Docker, 3. Terraform, 4. Ansible, 5. Helm, 6. ArgoCD, 7. AWS EKS, 8. CI/CD, 9. Jenkins, 10. GitLab CI, 11. GitHub Actions, 12. Trivy, 13. SonarQube, 14. Prometheus, 15. Grafana, 16. Alertmanager, 17. ELK Stack, 18. Elasticsearch, 19. Logstash, 20. Kibana, 21. Velero, 22. Harbor Registry, 23. Nginx Ingress, 24. Kong Gateway, 25. containerd, 26. Apache Kafka, 27. Redis, 28. PostgreSQL, 29. TimescaleDB, 30. MongoDB, 31. pgvector, 32. MinIO, 33. Python, 34. Rust, 35. FastAPI, 36. SQL, 37. Bash, 38. Linux, 39. YAML, 40. Jinja2, 41. PySpark, 42. Azure Databricks, 43. Delta Lake, 44. Azure Data Factory, 45. ADLS Gen2, 46. MLflow, 47. MLOps, 48. GitOps, 49. Site Reliability Engineering, 50. Infrastructure as Code (IaC)

### 8. Certifications
* **Microsoft Certified: Azure Fundamentals (AZ-900)** — Microsoft (2025)
* **Microsoft Certified: Security Operations Analyst Associate (SC-200)** — Microsoft (2025)
* **Certified Kubernetes Administrator (CKA)** — Cloud Native Computing Foundation (In Progress)

---

## Part IV — Required Interactive Authentication Checklist (Zero Bypasses)

> **Policy:** Never bypass CAPTCHAs, OTPs, or platform authentication controls. Complete these manual steps in an interactive browser/terminal session after M3 deploys code to the VM.

1. **Naukri Interactive Session Refresh (Unblocks Nov 18–19 OTP/CAPTCHA Freeze):**
   * On the VM (`ssh -i ~/.ssh/ssh-key-2026-08-30.key ubuntu@130.210.19.226`) or via X11/VNC headed Chrome:
     ```bash
     cd /home/ubuntu/Resume
     .venv/bin/python -m naukari_pro auth
     ```
   * Complete the Naukri email/SMS OTP or CAPTCHA manually so the persistent Playwright profile saves fresh session cookies.
   * Then run `sync_naukri_live_profile.py` / `verify_naukri_live_profile_dom.py` or paste Part II copy directly in the Naukri dashboard and upload `Lavkush_Kumar_MLOps_Resume.pdf`.
2. **LinkedIn Cookie Refresh & `.env:31` Verification:**
   * Log into `https://www.linkedin.com/in/lavkushry/` in Chrome, copy fresh `li_at` and `JSESSIONID` cookies.
   * Update `LINKEDIN_LI_AT` and `LINKEDIN_JSESSIONID` in `.env` (ensure `LINKEDIN_JSESSIONID` uses clean single-quoted or non-nested-quote formatting so `python-dotenv` parses line 31 with zero warnings).
   * Manually apply Part III updates (Headline, Open-to-Work, About, CGI/HFCL/Apprentice/Stipe Experience, 3 GitHub Projects, Skills, Certifications) on LinkedIn.
3. **Manual Review of 9 Quarantined CAPTCHA Items (`attention_queue.json`):**
   * Inspect `attention_queue.json` on the VM for the **9** jobs halted at CAPTCHA / human-verification gates (`status="NEEDS_HUMAN_ATTENTION"` / CAPTCHA) and submit/skip them manually in a real browser.

---

## Changelog

### Update: November 22, 2026
- Created initial 5-area evidence-backed selection diagnosis (F1), copy-ready Naukri & LinkedIn profile copy grounded in `AGENTS.md §9` and `01_FACT_MATRIX.md` (F5), and interactive user authentication checklist (zero CAPTCHA/auth bypasses).
