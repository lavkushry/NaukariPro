# NaukariPro v2.0 — Phase-5 RE-EXAM (2026-11-08)

**Examiner:** Independent re-exam (post F1–F5 fixes)  
**Scope:** `hammer_safe.py`, `governed_apply/{confirmation,approval,fill_verify}.py`, `resume_gen/claim_validator.py`, `security/{canary,pii}.py`, `api/app.py`  
**Charter:** Verify prior criticals hold; hunt for **new** fail-open criticals (Hammer Oath). **No production code changed.**

---

## Executive summary

| Item | Result |
|------|--------|
| **F1–F5 regression probes** | **5 / 5 PASS** |
| **New critical fail-open count** | **2** (target was 0) |

Prior fixes for confirmation negation, SSRF literals (hex/octal/nip), `NUMBER_RE` unit suffixes, `AIza` in `security.pii`, and ledger confirmation proof are **holding** on the original reproduction snippets.

Two **new** critical issues were reproduced: (1) URL-only confirmation ignores error/negation in `page_text`, allowing `applied` ledger state on failed submits; (2) Unicode alternate-digit host labels pass `validate_job_url` while resolving to `127.0.0.1`.

---

## F1–F5 fix verification

| ID | Issue (original) | Probe result | Verdict |
|----|------------------|--------------|---------|
| **F1** | Negated page text still confirms submit | `detect_submission_confirmation(page_text="error: application submitted failed").confirmed` → `False`; `GovernedApplyPipeline.run_job(..., page_text same, page_url="")` → `status="filled"`, `submitted=False` | **PASS** |
| **F2** | Hex/octal/nip SSRF | `validate_job_url` on `http://0x7f000001/`, `http://0177.0.0.1/`, `http://127.0.0.1.nip.io/` → `ValidationError` (SSRF-blocked) | **PASS** |
| **F3** | `ms` metrics not grounded | `NUMBER_RE.findall("...999ms.")` → `['400ms','999ms']`; `validate_text(...).ok` → `False` | **PASS** |
| **F4** | `AIza` not redacted in `security.pii` | `redact_pii(leak)` → `[REDACTED_SECRET]`; `secrets_in_text(leak)` non-empty | **PASS** |
| **F5** | Ledger without confirmation proof | `record_confirmed_submit(..., confirmation_text=None, confirmation_url=None)` → `IntegrityError` | **PASS** |

### F1 probe (representative)

```python
from naukari_pro.governed_apply.confirmation import detect_submission_confirmation
from naukari_pro.governed_apply.pipeline import GovernedApplyPipeline
import tempfile
from pathlib import Path

assert not detect_submission_confirmation(
    page_text="error: application submitted failed"
).confirmed

pipe = GovernedApplyPipeline(
    {"email": "x@y.com"}, dry_run=False, auto_submit=True,
    db_path=Path(tempfile.mkdtemp()) / "p.db",
)
res = pipe.run_job(
    {"url": "https://example.com/jobs/1", "fit_score": 90, "coverage_pct": 80},
    dom_fields=[],
    page_text="error: application submitted failed",
    page_url="",
    approved=True,
)
assert res.status == "filled" and res.submitted is False
```

### F2 / F3 / F4 / F5 probes

Same snippets as `tests/hammer/PHASE5_EXAM_2026-11-08.md`; all raise or deny as expected after fixes.

---

## New critical fail-open findings

### F6 — URL confirmation bypasses error `page_text` (ledger marks applied)

| Field | Value |
|-------|-------|
| **Severity** | **critical** |
| **Module** | `naukari_pro/governed_apply/confirmation.py` → `detect_submission_confirmation`; coupling in `pipeline.py` → `run_job` |
| **Oath violation** | **Counts blocked as applied** — `/thanks`-style URL match confirms even when visible DOM text reports failure/negation. |

**Reproduction:**

```python
from naukari_pro.governed_apply.confirmation import detect_submission_confirmation
from naukari_pro.governed_apply.pipeline import GovernedApplyPipeline
import tempfile
from pathlib import Path

assert detect_submission_confirmation(
    page_text="SUBMIT FAILED PLEASE FIX ERRORS",
    page_url="https://boards.example/thanks",
).confirmed is True  # fail-open: URL match ignores error text

pipe = GovernedApplyPipeline(
    {"email": "a@b.com"}, dry_run=False, auto_submit=True,
    db_path=Path(tempfile.mkdtemp()) / "p.db",
)
res = pipe.run_job(
    {"url": "https://boards.example/job/1", "fit_score": 90, "coverage_pct": 80},
    dom_fields=[],
    page_text="SUBMIT FAILED PLEASE FIX ERRORS",
    page_url="https://boards.example/thanks",
    approved=True,
)
assert res.status == "applied" and res.submitted is True
```

**Root cause:** `_NEGATION_RE` runs only when a **text** success pattern matches (`if text_m and _NEGATION_RE.search(text)`). A URL pattern match alone (`url_m`) returns `confirmed=True` without considering negation or errors in `page_text`.

---

### F7 — Unicode alternate-digit host literals bypass SSRF gate

| Field | Value |
|-------|-------|
| **Severity** | **critical** |
| **Module** | `naukari_pro/hammer_safe.py` → `validate_job_url` / `_is_blocked_ssrf_host` |
| **Oath violation** | **SSRF** — job URLs normalize to public hosts while `socket.getaddrinfo` resolves to `127.0.0.1`. |

**Reproduction:**

```python
import socket
from urllib.parse import urlparse
from naukari_pro.hammer_safe import validate_job_url

for url in (
    "http://①②⑦.⓪.⓪.①/",      # circled digits
    "http://１２７．０．０．１/",  # fullwidth
):
    host = urlparse(url).hostname
    validate_job_url(url)  # does NOT raise — fail-open
    assert socket.getaddrinfo(host, 80)[0][4][0] == "127.0.0.1"
```

**Root cause:** F2 hardening covers dotted-decimal, hex, octal, decimal, and nip/sslip labels, but not Unicode digit variants that the resolver maps to loopback.

---

## New criticals count

**2** (`F6`, `F7`)

---

## Additional probes (not elevated to critical)

| Area | Observation | Severity |
|------|-------------|----------|
| `canary.CanaryTypeHook` | Zero-width insert `s\u200becrettoken` → `allow_type` True (same as initial exam) | High (not on apply/ledger oath path alone) |
| `fill_verify.verify_field` | `require_commit=False` with wrong `dom_value` → `ok=True` | High; pipeline does not rely on this flag for submit |
| `fill_verify.verify_form([])` | `all_ok=False` (empty form fail-closed) | OK |
| `approval.record_confirmed_submit` | Whitespace-only proof refused; single-char proof allowed by design | OK |
| `api/app.py` | `emit` path uses `redact_secrets` + `redact_pii`; webhook delivery is queued only (no live SSRF in-module) | OK (review) |
| `claim_validator` | Spaced `999 ms` fails grounding; `%` / `x` / `lakhs` mismatches fail | OK |

---

## Methodology

1. Re-ran original F1–F5 Python probes from repo root (`python3`, 2026-11-08).
2. Read scoped source files; traced `GovernedApplyPipeline.run_job` confirmation → ledger.
3. Hostile probes: extended SSRF literals, confirmation URL/text split, ledger proof edge cases, PII parity, canary typing hook.
4. Correlated SSRF bypass hosts with `socket.getaddrinfo` (no outbound HTTP).

---

## Post-exam remediation (parent agent)

F6/F7 were fixed in-tree the same day:

- `confirmation.py` — any `_NEGATION_RE` match voids **both** text and URL confirmation.
- `hammer_safe.py` — NFKC + circled/fullwidth digit normalize before SSRF host checks.
- Regressions: `test_p5c_f6_url_confirm_voided_by_error_text`, `test_p5c_f7_unicode_digit_ssrf_blocked`.

**Residual new criticals after remediation: 0** (probes + regressions green).

## Changelog

### 2026-11-08

- Phase-5 RE-EXAM report: F1–F5 verified pass; **2** new criticals (F6 URL/text confirmation split, F7 Unicode IP SSRF).
- Same-day fix loop closed F6/F7; residual new criticals **0**.
