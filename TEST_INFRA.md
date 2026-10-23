# E2E Test Infra: Autonomous Career Optimization Platform

## Test Philosophy
- Opaque-box, requirement-driven derived from `ORIGINAL_REQUEST.md` and user-facing specifications.
- Fully decoupled from live external network dependencies so tests run 100% offline and deterministic on both local macOS and remote Linux VM (`ubuntu@141.148.195.233`).
- Methodology: 4-tier systematic approach (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, Real-World Workload Testing).

---

## Feature Inventory & Test Matrix
| # | Feature | Source | Tier 1 (Coverage) | Tier 2 (Boundaries) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---------|--------|:-----------------:|:-------------------:|:-----------------:|:-----------------:|
| F1 | Keyword Saturation & SEO | R1 (SEO) | 5 test cases | 5 test cases | ✓ | ✓ |
| F2 | 17 Bullets 5-Stage Formula | R1 (SEO) | 5 test cases | 5 test cases | ✓ | ✓ |
| F3 | 1-Page ATS PDF Compilation | R1 (SEO) | 5 test cases | 5 test cases | ✓ | ✓ |
| F4 | Match Score Gating (>=70%) | R2 (Engine) | 5 test cases | 5 test cases | ✓ | ✓ |
| F5 | Questionnaire Screening Auto-Answer | R2 (Engine) | 5 test cases | 5 test cases | ✓ | ✓ |
| F6 | Multi-Channel Sourcing (HN/LinkedIn/Portals) | R2 (Engine) | 5 test cases | 5 test cases | ✓ | ✓ |
| F7 | Structured Dry-Run Application Payload | R2 & R4 | 5 test cases | 5 test cases | ✓ | ✓ |
| F8 | Recruiter 100k Benchmark Analytics | R3 (Analytics) | 5 test cases | 5 test cases | ✓ | ✓ |
| F9 | Tracker Excel Schema & Logging | R3 (Tracking) | 5 test cases | 5 test cases | ✓ | ✓ |
| F10| Cloud Daemon & Singleton Locking | R4 (Cloud) | 5 test cases | 5 test cases | ✓ | ✓ |

---

## Test Architecture
- **Test Runner**: `pytest` executing `tests/test_offline_suite.py`
- **Invocation**: `.venv/bin/pytest tests/test_offline_suite.py -v`
- **Pass/Fail Semantics**: 100% passing test cases with exit code 0. Zero skipped or failed assertions.
- **Isolation**: Uses `tmp_path` fixtures for file creation (Excel, PDF, JSON), mocked DOM responses, and synthetic payload objects without live browser or network access.
- **Portability**: Verified on macOS (Darwin arm64) and Linux (Ubuntu 22.04 x86_64).

---

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Offline Autonomous Apply Cycle: Job discovery -> match score filter (>=70%) -> chatbot screening -> Excel tracker append | F4, F5, F7, F9 | High |
| 2 | Resdex Profile & Benchmark Refresh: Recruiter search metric extraction -> 100k velocity projection -> performance tracker append | F1, F8, F9 | High |
| 3 | Multi-Channel Sourcing & ATS Portal Dry-Run: HN/LinkedIn query generation -> ATS form classification -> resume attachment -> dry-run payload | F3, F6, F7, F9 | High |
| 4 | ATS Resume Compilation & Plain-Text Verification: Dynamic config loading -> ReportLab 1-page PDF generation -> pypdf plain-text parsing & quality score | F1, F2, F3 | Medium |
| 5 | Cloud Daemon Singleton Lock & WAF Proxy Protection: Overlapping run prevention -> process flock -> Playwright proxy config verification | F7, F10 | Medium |

---

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per core feature verifying positive functional requirements.
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature covering empty inputs, thresholds (69% vs 70%), missing columns, max character counts.
- **Tier 3 (Pairwise Combinations)**: Cross-feature tests verifying data contracts (e.g. match score -> payload -> Excel logging).
- **Tier 4 (Real-World Scenarios)**: 5 end-to-end integration workflows simulating full pipeline operations offline.
