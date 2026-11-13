"""
Per-tenant ATS account vault (H4).
Secrets live in gitignored portal_accounts.json — never logged.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from naukari_pro.config import WORKSPACE_DIR
from naukari_pro.modules.candidate_profile import load_hybrid_profile

VAULT_PATH = Path(WORKSPACE_DIR) / "portal_accounts.json"
MAX_RESETS_PER_TENANT_PER_RUN = 1


def _tenant_key_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        host = host.replace("www.", "")
        # Workday tenant: company.wdN.myworkdayjobs.com
        m = re.match(r"^([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com$", host)
        if m:
            return f"workday:{m.group(1)}"
        if "greenhouse.io" in host:
            return f"greenhouse:{host}"
        if "lever.co" in host:
            return f"lever:{host}"
        if "ashbyhq.com" in host:
            return f"ashby:{host}"
        return f"ats:{host}"
    except Exception:
        return f"ats:{url[:64]}"


def _gen_password(length: int = 16) -> str:
    """Workday tenants (e.g. Fractal) require upper+lower+digit+special — guarantee all four."""
    length = max(12, int(length or 16))
    specials = "!@#$%^&*"
    # Ensure one of each class, then fill the rest from the full alphabet.
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(specials),
    ]
    alphabet = string.ascii_letters + string.digits + specials
    rest = [secrets.choice(alphabet) for _ in range(length - len(required))]
    chars = required + rest
    # Shuffle so required chars are not always prefix-positioned
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def _meets_workday_password_policy(password: str) -> bool:
    p = password or ""
    return (
        len(p) >= 8
        and any(c.isupper() for c in p)
        and any(c.islower() for c in p)
        and any(c.isdigit() for c in p)
        and any(c in "!@#$%^&*" for c in p)
    )


def harden_password(password: str) -> str:
    """Append missing Workday policy classes; regenerate if still weak."""
    p = password or ""
    if not any(c.isupper() for c in p):
        p += "A"
    if not any(c.islower() for c in p):
        p += "a"
    if not any(c.isdigit() for c in p):
        p += "1"
    if not any(c in "!@#$%^&*" for c in p):
        p += "!"
    if len(p) < 8 or not _meets_workday_password_policy(p):
        return _gen_password(16)
    return p


class PortalAccountManager:
    """Lookup / create / reset lifecycle for ATS tenant accounts."""

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = Path(vault_path) if vault_path else VAULT_PATH
        self._reset_counts: Dict[str, int] = {}
        self._ensure_vault()

    def _ensure_vault(self) -> None:
        if not self.vault_path.exists():
            self.vault_path.write_text(
                json.dumps({"tenants": {}, "version": 1}, indent=2) + "\n",
                encoding="utf-8",
            )

    def _load(self) -> Dict[str, Any]:
        self._ensure_vault()
        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"tenants": {}, "version": 1}

    def _save(self, data: Dict[str, Any]) -> None:
        tmp = self.vault_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp, self.vault_path)

    def get_account(self, url: str) -> Optional[Dict[str, Any]]:
        key = _tenant_key_from_url(url)
        data = self._load()
        return data.get("tenants", {}).get(key)

    def ensure_account(self, url: str, email: Optional[str] = None) -> Dict[str, Any]:
        """Return existing tenant account or create a new vault entry (password generated)."""
        key = _tenant_key_from_url(url)
        data = self._load()
        tenants = data.setdefault("tenants", {})
        if key in tenants:
            acct = tenants[key]
            # Self-heal vault passwords that predate Workday complexity guarantees
            raw = acct.get("password") or ""
            fixed = harden_password(raw)
            if fixed != raw:
                acct["password"] = fixed
                acct["verified"] = False  # old password may not match tenant
                self._save(data)
            return acct

        profile = load_hybrid_profile()
        acct = {
            "tenant_key": key,
            "email": email or profile.get("applicantEmail") or profile.get("email"),
            "password": _gen_password(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_login_at": None,
            "verified": False,
            "reset_count_total": 0,
            "url_sample": url,
        }
        tenants[key] = acct
        self._save(data)
        return acct

    def mark_verified(self, url: str) -> None:
        key = _tenant_key_from_url(url)
        data = self._load()
        if key in data.get("tenants", {}):
            data["tenants"][key]["verified"] = True
            data["tenants"][key]["last_login_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save(data)

    def can_reset(self, url: str) -> bool:
        key = _tenant_key_from_url(url)
        return self._reset_counts.get(key, 0) < MAX_RESETS_PER_TENANT_PER_RUN

    def rotate_password(self, url: str) -> Optional[Dict[str, Any]]:
        """Max 1 reset per tenant per run."""
        if not self.can_reset(url):
            return None
        key = _tenant_key_from_url(url)
        data = self._load()
        acct = data.get("tenants", {}).get(key)
        if not acct:
            return None
        acct["password"] = _gen_password()
        acct["reset_count_total"] = int(acct.get("reset_count_total", 0)) + 1
        acct["last_reset_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._reset_counts[key] = self._reset_counts.get(key, 0) + 1
        self._save(data)
        return acct

    def resolve_auth_wall(
        self,
        url: str,
        page=None,
        mail_reader=None,
    ) -> Dict[str, Any]:
        """
        Workflow for account walls: ensure vault account, optionally poll mail for verify link.
        Does not bypass captchas. Returns status for the ATS handler.
        """
        acct = self.ensure_account(url)
        result = {
            "tenant_key": acct["tenant_key"],
            "email": acct["email"],
            "has_password": bool(acct.get("password")),
            "verified": bool(acct.get("verified")),
            "status": "ACCOUNT_READY",
            "verification_link": None,
        }
        if mail_reader is not None and not acct.get("verified"):
            try:
                link = mail_reader.fetch_verification_link(max_age_minutes=20)
                if link:
                    result["verification_link"] = link
                    result["status"] = "VERIFY_LINK_FOUND"
            except Exception as e:
                result["status"] = f"MAIL_POLL_ERROR: {e}"
        return result
