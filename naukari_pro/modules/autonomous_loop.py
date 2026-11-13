"""
Always-on closed-loop autonomy helpers for Beast / external ATS.

- Drain incomplete portal rows (Ready for Review / SUBMIT_NOT_FOUND / SIGNIN_WALL)
- Gmail IMAP OTP / verify-link polling (Workday + Greenhouse)
- CAPTCHA attention: M5 resolver chain → human headed wait (no silent SSO/legal bypass)
"""

from __future__ import annotations

import email
import email.utils
import imaplib
import json
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from naukari_pro.config import WORKSPACE_DIR
from naukari_pro.governed_apply.attention import AttentionQueue, BlockerClass

logger = logging.getLogger("naukariPro.AutonomousLoop")

DB_PATH = Path(WORKSPACE_DIR) / "applied_jobs.db"
ATTENTION_PATH = Path(WORKSPACE_DIR) / "attention_queue.json"
USED_EMAIL_CODES: set = set()

DRAIN_STATUSES = (
    "Form Auto-Filled",
    "Form Auto-Filled (Ready for Review)",
    "FALLBACK (SUBMIT_NOT_FOUND)",
    "FALLBACK (CLICKED_NO_CONFIRMATION)",
    "FALLBACK (SIGNIN_WALL)",
    "FALLBACK (CAPTCHA)",
)


@dataclass
class DrainResult:
    evaluated: int = 0
    submitted: int = 0
    skipped: int = 0
    needs_human: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)


def _gmail_creds() -> Tuple[str, str]:
    from dotenv import load_dotenv

    load_dotenv()
    user = os.getenv("GMAIL_USER", "lav84095@gmail.com")
    pwd = os.getenv("GMAIL_APP_PASSWORD", "")
    return user, pwd


def fetch_ats_email_code(
    *,
    since_ts: float = 0.0,
    timeout_sec: float = 60.0,
    subject_keywords: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """Poll Gmail IMAP for a fresh ATS verification / security code."""
    keywords = [k.lower() for k in (subject_keywords or (
        "security code",
        "verification code",
        "verify your",
        "verify your email",
        "one-time",
        "otp",
        "workday",
        "confirm your email",
    ))]
    user, pwd = _gmail_creds()
    if not pwd:
        logger.warning("GMAIL_APP_PASSWORD unset — cannot poll IMAP OTP")
        return None

    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(user, pwd)
            mail.select("INBOX")
            status, data = mail.search(None, "ALL")
            ids = data[0].split() if data and data[0] else []
            for mid in reversed(ids[-25:]):
                status, mdata = mail.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(mdata[0][1])
                subj = (msg.get("Subject") or "").lower()
                if not any(k in subj for k in keywords):
                    continue
                date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                msg_epoch = email.utils.mktime_tz(date_tuple) if date_tuple else 0
                if since_ts > 0 and msg_epoch > 0 and msg_epoch < (since_ts - 30):
                    continue

                clean_text = ""
                for part in msg.walk():
                    ctype = part.get_content_type()
                    raw = part.get_payload(decode=True)
                    if not raw:
                        continue
                    text = raw.decode("utf-8", errors="ignore")
                    if ctype == "text/html":
                        text = re.sub(r"<[^>]+>", " ", text)
                    if ctype in ("text/plain", "text/html"):
                        clean_text += " " + text
                clean_text = re.sub(r"\s+", " ", clean_text).strip()

                match = (
                    re.search(
                        r"(?:security code|verification code|your code is|enter the code|otp)[:\s]+([a-zA-Z0-9]{4,8})",
                        clean_text,
                        re.I,
                    )
                    or re.search(r"\b([A-Z0-9]{6,8})\b", clean_text)
                )
                if match:
                    code = match.group(1)
                    if code in USED_EMAIL_CODES:
                        continue
                    USED_EMAIL_CODES.add(code)
                    mail.logout()
                    return code
            mail.logout()
        except Exception as exc:  # noqa: BLE001
            logger.debug("IMAP poll notice: %s", exc)
        time.sleep(2.5)
    return None


def fetch_ats_verification_link(
    *,
    since_ts: float = 0.0,
    timeout_sec: float = 90.0,
) -> Optional[str]:
    """Poll Gmail for a Workday/ATS email verification URL."""
    user, pwd = _gmail_creds()
    if not pwd:
        return None
    start = time.time()
    link_re = re.compile(
        r"https?://[^\s\"'<>]*(?:myworkdayjobs|workday|verify|confirm|activate)[^\s\"'<>]*",
        re.I,
    )
    while time.time() - start < timeout_sec:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(user, pwd)
            mail.select("INBOX")
            status, data = mail.search(None, "ALL")
            ids = data[0].split() if data and data[0] else []
            for mid in reversed(ids[-20:]):
                status, mdata = mail.fetch(mid, "(RFC822)")
                msg = email.message_from_bytes(mdata[0][1])
                subj = (msg.get("Subject") or "").lower()
                if not any(k in subj for k in ("verify", "confirm", "activate", "workday", "account")):
                    continue
                date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                msg_epoch = email.utils.mktime_tz(date_tuple) if date_tuple else 0
                if since_ts > 0 and msg_epoch > 0 and msg_epoch < (since_ts - 30):
                    continue
                body = ""
                for part in msg.walk():
                    raw = part.get_payload(decode=True)
                    if raw:
                        body += " " + raw.decode("utf-8", errors="ignore")
                m = link_re.search(body)
                if m:
                    mail.logout()
                    return m.group(0).rstrip(").,]>\"'")
            mail.logout()
        except Exception as exc:  # noqa: BLE001
            logger.debug("IMAP verify-link notice: %s", exc)
        time.sleep(3.0)
    return None


def list_incomplete_portal_jobs(limit: int = 25, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load career_portal rows that need autonomous re-submit."""
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        return []
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in DRAIN_STATUSES)
        rows = conn.execute(
            f"""
            SELECT id, job_id, company, title, job_url, status, match_score, applied_at
            FROM applied_jobs
            WHERE platform LIKE '%career%'
              AND status IN ({placeholders})
              AND job_url IS NOT NULL
              AND job_url != ''
              AND lower(job_url) NOT LIKE '%naukri.com%'
            ORDER BY applied_at DESC
            LIMIT ?
            """,
            (*DRAIN_STATUSES, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def resolve_captcha_with_attention(
    page: Any,
    *,
    job_url: str = "",
    company: str = "",
    board: str = "career_portal",
    headed_wait_sec: int = 180,
) -> Dict[str, Any]:
    """
    Run M5 captcha chain. Vendor only if CAPTCHA_MODE includes vendor + keys.
    Human path: headed pause until challenge clears or timeout.
    Never claims SSO/legal attestation as solved.
    """
    from naukari_pro.captcha.resolver import CaptchaResolverChain, EXIT_CAPTCHA_BLOCKED

    html = ""
    try:
        html = page.content() if page and hasattr(page, "content") else ""
    except Exception:
        html = ""

    chain = CaptchaResolverChain(board=board, company=company)
    result = chain.resolve_html(html, page_url=job_url or getattr(page, "url", "") or "")
    out = {
        "resolved": bool(result.resolved),
        "resolved_by": result.resolved_by,
        "detail": result.detail,
        "exit_code": result.exit_code,
        "token": result.token,
    }
    if result.resolved:
        return out

    queue = AttentionQueue()
    queue.push(BlockerClass.CAPTCHA, job_url or "", result.detail or "needs_human")
    try:
        ATTENTION_PATH.write_text(
            json.dumps(
                [
                    {
                        "blocker": i.blocker.value,
                        "job_url": i.job_url,
                        "detail": i.detail,
                        "status": i.status,
                    }
                    for i in queue.items
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass

    print(
        f"    [CAPTCHA ATTENTION] Needs human for {company or job_url}. "
        f"Waiting up to {headed_wait_sec}s for challenge clear (solve in browser)..."
    )
    try:
        if page and hasattr(page, "bring_to_front"):
            page.bring_to_front()
    except Exception:
        pass

    deadline = time.time() + max(30, int(headed_wait_sec))
    while time.time() < deadline:
        try:
            html2 = page.content() if page else ""
            recheck = chain.resolve_html(html2, page_url=job_url or getattr(page, "url", "") or "")
            if recheck.resolved or recheck.detail == "no_captcha":
                still = None
                try:
                    from naukari_pro.session import detect_challenge

                    still = detect_challenge(page) if page else None
                except Exception:
                    still = None
                if not still:
                    out.update(
                        {
                            "resolved": True,
                            "resolved_by": "human",
                            "detail": "human_cleared",
                            "exit_code": 0,
                        }
                    )
                    return out
        except Exception:
            pass
        time.sleep(3.0)

    out["exit_code"] = EXIT_CAPTCHA_BLOCKED
    out["detail"] = "needs_human_timeout"
    return out


def drain_incomplete_portal_applies(
    *,
    limit: int = 15,
    headless: bool = False,
    dry_run: bool = False,
    universal_apply: bool = True,
) -> DrainResult:
    """Re-attempt incomplete external portal applications with auto_submit=True."""
    from naukari_pro.modules.career_portals import CareerPortalFiller, FillResult

    _ = universal_apply  # reserved for future feed filtering
    jobs = list_incomplete_portal_jobs(limit=limit)
    result = DrainResult(evaluated=len(jobs))
    if not jobs:
        print("  [drain] No incomplete career_portal rows to re-submit.")
        return result

    print(f"  [drain] Re-submitting {len(jobs)} incomplete external ATS applications (auto_submit=True)...")
    filler = CareerPortalFiller()
    for job in jobs:
        company = job.get("company") or "Company"
        title = job.get("title") or "Role"
        url = job.get("job_url") or ""
        score = job.get("match_score")
        try:
            score_i = int(float(score)) if score is not None else None
        except (TypeError, ValueError):
            score_i = None
        print(f"  [*] Drain: {title} @ {company}")
        try:
            fill_res = filler.fill(
                portal_url=url,
                company=company,
                role=title,
                headless=headless,
                dry_run=dry_run,
                match_score=score_i,
                auto_submit=True,
                allow_retry=True,
            )
            if isinstance(fill_res, FillResult):
                status = fill_res.status or ("Submitted (Confirmed)" if fill_res.success else "UNKNOWN")
                ok = bool(fill_res.success)
            elif isinstance(fill_res, tuple):
                status = "DRY_RUN"
                ok = False
            elif isinstance(fill_res, dict):
                status = str(fill_res.get("status", "UNKNOWN"))
                ok = bool(fill_res.get("success"))
            else:
                status = str(fill_res)
                ok = "Submitted" in status

            if ok or (isinstance(status, str) and "Submitted" in status and "FALLBACK" not in status):
                result.submitted += 1
            elif isinstance(status, str) and any(k in status for k in ("CAPTCHA", "SIGNIN", "Ready for Review")):
                result.needs_human += 1
            else:
                result.skipped += 1
            result.items.append({"company": company, "title": title, "status": status, "url": url})
        except Exception as exc:  # noqa: BLE001
            result.skipped += 1
            result.items.append({"company": company, "title": title, "status": f"ERROR:{exc}", "url": url})

    print(
        f"  [drain] Done: submitted={result.submitted} needs_human={result.needs_human} "
        f"skipped={result.skipped} evaluated={result.evaluated}"
    )
    return result
