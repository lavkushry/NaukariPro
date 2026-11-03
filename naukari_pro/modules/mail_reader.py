"""
IMAP mail reader for ATS account verification (H5).
Uses GMAIL_APP_PASSWORD from .env — never logs secrets.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

VERIFY_LINK_RE = re.compile(
    r"https?://[^\s\"'<>]+(?:verify|confirm|activation|token|otp|signup|register|invite)[^\s\"'<>]*",
    re.IGNORECASE,
)
GENERIC_HTTPS_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
OTP_RE = re.compile(r"\b(\d{4,8})\b")


class IMAPMailReader:
    """Polls Gmail IMAP for ATS verification links and OTP codes."""

    def __init__(
        self,
        host: str = "imap.gmail.com",
        user: Optional[str] = None,
        password: Optional[str] = None,
        mailbox: str = "INBOX",
    ):
        self.host = host
        self.user = user or os.environ.get("GMAIL_USER") or os.environ.get("NAUKRI_EMAIL") or ""
        self.password = password or os.environ.get("GMAIL_APP_PASSWORD") or ""
        self.mailbox = mailbox

    def _require_creds(self) -> None:
        if not self.user or not self.password:
            raise RuntimeError(
                "IMAP credentials missing. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env"
            )

    def test_connection(self) -> Dict[str, Any]:
        """CLI/mail-test probe — does not print password."""
        try:
            self._require_creds()
            with imaplib.IMAP4_SSL(self.host) as conn:
                conn.login(self.user, self.password)
                typ, data = conn.select(self.mailbox, readonly=True)
                count = int(data[0]) if typ == "OK" and data and data[0] else 0
                return {
                    "ok": True,
                    "host": self.host,
                    "user": self.user,
                    "mailbox": self.mailbox,
                    "message_count": count,
                }
        except Exception as e:
            return {
                "ok": False,
                "host": self.host,
                "user": self.user or "(unset)",
                "error": str(e),
            }

    def _connect(self) -> imaplib.IMAP4_SSL:
        self._require_creds()
        conn = imaplib.IMAP4_SSL(self.host)
        conn.login(self.user, self.password)
        conn.select(self.mailbox)
        return conn

    def _decode_part(self, part) -> str:
        payload = part.get_payload(decode=True)
        if payload is None:
            return str(part.get_payload() or "")
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except Exception:
            return payload.decode("utf-8", errors="replace")

    def _message_body(self, msg) -> str:
        parts: List[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype in ("text/plain", "text/html"):
                    parts.append(self._decode_part(part))
        else:
            parts.append(self._decode_part(msg))
        return "\n".join(parts)

    def _within_age(self, msg, max_age_minutes: int) -> bool:
        try:
            dt = parsedate_to_datetime(msg.get("Date"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - dt <= timedelta(minutes=max_age_minutes)
        except Exception:
            return True

    def fetch_recent_messages(
        self,
        sender_filter: str = "",
        subject_filter: str = "",
        max_age_minutes: int = 15,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            criteria = ["ALL"]
            if sender_filter:
                criteria = [f'(FROM "{sender_filter}")']
            typ, data = conn.search(None, *criteria if len(criteria) == 1 else criteria[0])
            if typ != "OK" or not data or not data[0]:
                return []
            ids = data[0].split()[-limit:]
            out: List[Dict[str, Any]] = []
            for mid in reversed(ids):
                typ, msg_data = conn.fetch(mid, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                if not self._within_age(msg, max_age_minutes):
                    continue
                subj = msg.get("Subject", "")
                if subject_filter and subject_filter.lower() not in subj.lower():
                    continue
                body = self._message_body(msg)
                out.append(
                    {
                        "subject": subj,
                        "from": msg.get("From", ""),
                        "date": msg.get("Date", ""),
                        "body": body,
                    }
                )
            return out
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def fetch_verification_link(
        self,
        sender_filter: str = "",
        max_age_minutes: int = 10,
        poll_seconds: int = 0,
        poll_interval: float = 5.0,
    ) -> Optional[str]:
        deadline = time.time() + max(0, poll_seconds)
        while True:
            for msg in self.fetch_recent_messages(
                sender_filter=sender_filter, max_age_minutes=max_age_minutes
            ):
                body = msg.get("body", "")
                m = VERIFY_LINK_RE.search(body)
                if m:
                    return m.group(0).rstrip(").,]>\"'")
                # Fallback: first https link in verification-ish subjects
                subj = (msg.get("subject") or "").lower()
                if any(k in subj for k in ("verify", "confirm", "activate", "code", "otp")):
                    m2 = GENERIC_HTTPS_RE.search(body)
                    if m2:
                        return m2.group(0).rstrip(").,]>\"'")
            if time.time() >= deadline:
                return None
            time.sleep(poll_interval)

    def fetch_verification_code(
        self,
        sender_filter: str = "",
        max_age_minutes: int = 10,
        poll_seconds: int = 0,
        poll_interval: float = 5.0,
    ) -> Optional[str]:
        deadline = time.time() + max(0, poll_seconds)
        while True:
            for msg in self.fetch_recent_messages(
                sender_filter=sender_filter, max_age_minutes=max_age_minutes
            ):
                body = msg.get("body", "")
                # Prefer codes near verification keywords
                for m in OTP_RE.finditer(body):
                    code = m.group(1)
                    window = body[max(0, m.start() - 40) : m.end() + 40].lower()
                    if any(k in window for k in ("code", "otp", "verify", "passcode", "pin")):
                        return code
                m2 = OTP_RE.search(body)
                if m2 and any(
                    k in (msg.get("subject") or "").lower()
                    for k in ("code", "otp", "verify", "passcode")
                ):
                    return m2.group(1)
            if time.time() >= deadline:
                return None
            time.sleep(poll_interval)


def mail_test() -> Dict[str, Any]:
    """Entry used by `./naukariPro mail-test`."""
    reader = IMAPMailReader()
    result = reader.test_connection()
    if result.get("ok"):
        print(f"  [✓] IMAP OK — {result['user']} @ {result['host']} ({result['message_count']} msgs)")
    else:
        print(f"  [!] IMAP FAIL — {result.get('error')}")
    return result
