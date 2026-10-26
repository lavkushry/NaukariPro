# E2E Test Infra: Autonomous LinkedIn Career & Easy Apply Engine

## Test Philosophy
- Opaque-box, requirement-driven, derived from `ORIGINAL_REQUEST.md` (under `## 2026-10-26T04:35:51Z`) and user-facing specifications.
- 100% offline, deterministic execution decoupled from external network access to ensure instant and reliable testing on both local macOS and remote Linux ARM64 VM (`ubuntu@141.148.195.233`).
- Methodology: 4-tier systematic approach (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, Real-World Workload Testing).

---

## Feature Inventory & Test Matrix
| # | Feature Area | Source | Tier 1 (Coverage) | Tier 2 (Boundaries) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|--------------|--------|:-----------------:|:-------------------:|:-----------------:|:-----------------:|
| F1 | `li_at` Cookie Auth & Session Loading | R1 (Session) | 5 test cases | 5 test cases | ✓ | ✓ |
| F2 | Fingerprint & Anti-Detection Stealth | R1 (Session) | 5 test cases | 5 test cases | ✓ | ✓ |
| F3 | Checkpoint / Expiry Detection & Handling | R1 (Session) | 5 test cases | 5 test cases | ✓ | ✓ |
| F4 | CLI Diagnostic (`linkedin-verify`) | R1 (Session) | 5 test cases | 5 test cases | ✓ | ✓ |
| F5 | 7 Tech Hubs + Remote Search URL Generator | R2 (Search) | 5 test cases | 5 test cases | ✓ | ✓ |
| F6 | Multi-Keyword Query Strategy & Freshness | R2 (Search) | 5 test cases | 5 test cases | ✓ | ✓ |
| F7 | Job Card Parsing & Deduplication | R2 (Search) | 5 test cases | 5 test cases | ✓ | ✓ |
| F8 | Strict Match Score Gating (>=70%) | R2 (Search) | 5 test cases | 5 test cases | ✓ | ✓ |
| F9 | Easy Apply Modal Navigation & Step Tracking | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F10| Contact Info Auto-Fill (Phone, Email) | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F11| Resume Attachment & Selection | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F12| Screening Questionnaire Regex Solver | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F13| Uncheck Follow Company Checkbox | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F14| Submission Confirmation & Auto-Discard Flow | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F15| Rate Limiting & Safety Delays | R3 (Bot) | 5 test cases | 5 test cases | ✓ | ✓ |
| F16| Dedicated Tracker Sheet (`LinkedIn_Applications_Log`)| R4 (Tracking) | 5 test cases | 5 test cases | ✓ | ✓ |
| F17| 100% Offline Dry-Run Mode (`--dry-run`) | R4 (Tracking) | 5 test cases | 5 test cases | ✓ | ✓ |
| F18| CLI Runner Integration (`linkedin-apply`) | R4 (CLI) | 5 test cases | 5 test cases | ✓ | ✓ |
| F19| Offline Regression Suite Integrity | R4 (Testing) | 5 test cases | 5 test cases | ✓ | ✓ |
| F20| Cloud Daemon Integration (`agy_schedule_runner.sh`)| R4 (Cloud) | 5 test cases | 5 test cases | ✓ | ✓ |

---

## Test Architecture
- **Test Runner**: `pytest`
- **Primary Suite**: `tests/test_linkedin_suite.py`
- **Invocation**: `.venv/bin/pytest tests/test_linkedin_suite.py -v`
- **Pass/Fail Semantics**: 100% passing test cases with exit code 0. Zero failed assertions, zero unhandled errors.
- **Isolation**: Synthetic DOM mocks via unittest.mock / Playwright mock objects, temporary directory (`tmp_path`) fixtures for Excel workbook generation, zero live HTTP requests or live browser instances during test execution.
- **Portability**: Fully verified on macOS (Darwin arm64) and Linux (Ubuntu 22.04 / 24.04 aarch64 on `ubuntu@141.148.195.233`).

---

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | **End-to-End Dry-Run Application Cycle**: Query generator produces URL -> job parser extracts candidate cards -> match scorer evaluates JD (>=70% gate) -> Easy Apply bot fills mock modal (contact, resume, questions, uncheck follow company) -> validated payload logged to `LinkedIn_Applications_Log` sheet | F5, F7, F8, F9, F10, F11, F12, F13, F16, F17 | High |
| 2 | **Stealth Session Lifecycle & Diagnostic**: Cookie loader reads token -> injects stealth flags -> handles simulated valid profile response -> tests expired cookie -> tests checkpoint challenge detection -> CLI `linkedin-verify` formatted output | F1, F2, F3, F4 | Medium |
| 3 | **Screening Questionnaire Stress Matrix**: Runs 50+ diverse question patterns (numbers, radios, dropdowns, textareas) through regex solver asserting 100% compliance with candidate ground truth (2.5 YOE, 15 days notice, India authorization, willing to commute) | F12 | Medium |
| 4 | **Modal Error Recovery & Discard Safety**: Simulates unhandled or invalid step -> detects inline error -> triggers auto-discard flow (clicks Dismiss -> confirms Discard) -> returns graceful skip status without hanging | F9, F14, F15 | High |
| 5 | **Multi-Hub Search Matrix & Deduplication**: Generates queries across 7 tech hubs + Remote India -> simulates overlapping job results -> verifies deduplication against historical application tracker | F5, F6, F7, F16 | Medium |
| 6 | **Tracker Compatibility & Fallback**: Validates `LinkedIn_Applications_Log` worksheet creation with 10 canonical columns, freeze panes, LinkedIn Blue styling, and fallback append to `Applications_Log` when requested | F16, F17 | Medium |

---

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per core feature verifying positive functional requirements.
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature covering edge cases, missing cookies, 69% vs 70% match threshold, empty inputs, unhandled questions.
- **Tier 3 (Pairwise Combinations)**: Cross-module contracts (session -> search -> bot -> tracker -> CLI).
- **Tier 4 (Real-World Scenarios)**: ≥5 realistic end-to-end integration workflows.
