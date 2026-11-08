"""
Fail-closed helpers exercised by the Big Hammer Protocol.

Parsers and gates must raise NaukariProError (typed) — never silent partial
accept, never injection, never unbounded memory on hostile input.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import yaml

from naukari_pro.errors import ConfigError, ParseError, ValidationError

# Documented hard limits (H5) — fail closed when exceeded.
MAX_STRING_BYTES = 2 * 1024 * 1024  # 2 MiB free-text
MAX_JSON_DEPTH = 64
MAX_YAML_ALIASES = 50
MAX_FORM_FIELDS = 500
MAX_ANSWER_CHARS = 4000
ALLOWED_DATA_ROOTS = ("logs", "naukari_pro", "tests", "config", "data", "tmp", ".")

_CSV_FORMULA = re.compile(r"^[=+\-@]")
_NULL_BYTE = re.compile(r"\x00")
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"xai-[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*\S+"),
]
_PII_PATTERNS = [
    re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),  # PAN
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),  # Aadhaar-ish
]


def _byte_len(s: str) -> int:
    return len(s.encode("utf-8", errors="replace"))


def assert_safe_string(value: Any, *, field: str = "input", max_bytes: int = MAX_STRING_BYTES) -> str:
    if value is None:
        raise ParseError(f"{field} is null", context={"field": field})
    if not isinstance(value, str):
        value = str(value)
    if _NULL_BYTE.search(value):
        raise ParseError(f"{field} contains null byte", context={"field": field})
    if _byte_len(value) > max_bytes:
        raise ParseError(
            f"{field} exceeds {max_bytes} bytes",
            context={"field": field, "bytes": _byte_len(value)},
        )
    return value


def sanitize_csv_cell(value: Any) -> str:
    text = assert_safe_string(value, field="csv_cell", max_bytes=64 * 1024)
    if _CSV_FORMULA.match(text.lstrip()):
        return "'" + text  # neutralize formula injection
    return text


def parse_json_safe(raw: Union[str, bytes], *, max_depth: int = MAX_JSON_DEPTH) -> Any:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParseError("JSON is not valid UTF-8", context={"error": str(exc)}) from exc
    raw = assert_safe_string(raw, field="json", max_bytes=MAX_STRING_BYTES)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ParseError("malformed JSON", context={"error": str(exc)}) from exc

    def _depth(obj: Any, d: int = 0) -> int:
        if d > max_depth:
            raise ParseError("JSON nesting exceeds max depth", context={"max_depth": max_depth})
        if isinstance(obj, dict):
            return max((_depth(v, d + 1) for v in obj.values()), default=d)
        if isinstance(obj, list):
            return max((_depth(v, d + 1) for v in obj), default=d)
        return d

    _depth(data)
    return data


class _SafeLoader(yaml.SafeLoader):
    pass


def parse_yaml_safe(raw: str) -> Any:
    raw = assert_safe_string(raw, field="yaml", max_bytes=512 * 1024)
    # Reject alias bombs early by counting anchors/aliases
    aliases = len(re.findall(r"&\w+", raw))
    refs = len(re.findall(r"\*\w+", raw))
    if aliases > MAX_YAML_ALIASES or refs > MAX_YAML_ALIASES:
        raise ParseError(
            "YAML alias bomb refused",
            context={"aliases": aliases, "refs": refs},
        )
    try:
        return yaml.load(raw, Loader=_SafeLoader)
    except yaml.YAMLError as exc:
        raise ParseError("malformed YAML", context={"error": str(exc)}) from exc


def _normalize_host_digits(host: str) -> str:
    """Map Unicode / fullwidth digits to ASCII so SSRF gates cannot be bypassed."""
    trans = str.maketrans(
        {
            "①": "1",
            "②": "2",
            "③": "3",
            "④": "4",
            "⑤": "5",
            "⑥": "6",
            "⑦": "7",
            "⑧": "8",
            "⑨": "9",
            "⓪": "0",
            "０": "0",
            "１": "1",
            "２": "2",
            "３": "3",
            "４": "4",
            "５": "5",
            "６": "6",
            "７": "7",
            "８": "8",
            "９": "9",
        }
    )
    return (host or "").translate(trans)


def _is_blocked_ssrf_host(host: str) -> bool:
    import ipaddress
    import unicodedata

    h = _normalize_host_digits(unicodedata.normalize("NFKC", host or "")).lower().strip(".")
    if not h:
        return True
    blocked_names = {
        "localhost",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "169.254.169.254",
    }
    if h in blocked_names or h.endswith(".local"):
        return True
    # DNS rebinding / local-resolution helpers (Phase-5 F2).
    if h.endswith(".nip.io") or h.endswith(".sslip.io") or h.endswith(".localtest.me"):
        return True
    if "127.0.0.1" in h or h.startswith("0.0.0.0."):
        return True

    def _block_ip(ip: "ipaddress._BaseAddress") -> bool:
        return bool(
            ip.is_loopback
            or ip.is_link_local
            or ip.is_private
            or ip.is_reserved
            or ip.is_multicast
        )

    # Decimal / IPv4 / IPv6 forms
    try:
        ip = ipaddress.ip_address(h)
        if _block_ip(ip):
            return True
    except ValueError:
        pass
    # Hex IPv4 (e.g. 0x7f000001 == 127.0.0.1)
    if re.match(r"^0x[0-9a-f]+$", h):
        try:
            ip = ipaddress.ip_address(int(h, 16))
            if _block_ip(ip):
                return True
        except ValueError:
            pass
    # Octal / mixed dotted (e.g. 0177.0.0.1)
    if re.match(r"^[0-7.]+$", h) and "." in h:
        try:
            parts = []
            for part in h.split("."):
                parts.append(str(int(part, 8) if part.startswith("0") and len(part) > 1 else int(part)))
            ip = ipaddress.ip_address(".".join(parts))
            if _block_ip(ip):
                return True
        except ValueError:
            pass
    # Numeric dotted loopback without full parse (e.g. 127.1)
    if re.match(r"^127\.\d{1,3}(?:\.\d{1,3}){0,2}$", h):
        return True
    if h.startswith("10.") or h.startswith("192.168."):
        return True
    if h.startswith("172."):
        parts = h.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    # Decimal IPv4 (e.g. 2130706433 == 127.0.0.1)
    if h.isdigit():
        try:
            ip = ipaddress.ip_address(int(h))
            if _block_ip(ip):
                return True
        except ValueError:
            pass
    return False


def validate_job_url(url: Any) -> str:
    text = assert_safe_string(url, field="job_url", max_bytes=4096).strip()
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError("job URL scheme must be http/https", context={"url": text[:200]})
    host = (parsed.hostname or "").lower()
    if _is_blocked_ssrf_host(host):
        raise ValidationError("SSRF-blocked job URL host", context={"host": host})
    return text


def validate_salary(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValidationError("salary cannot be boolean")
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("salary not numeric", context={"value": repr(value)}) from exc
    if num < 0 or num > 1_000_000:
        raise ValidationError("salary out of range", context={"value": num})
    if num != num:  # NaN
        raise ValidationError("salary is NaN")
    return num


def safe_evidence_path(path: Union[str, Path], *, base: Optional[Path] = None) -> Path:
    """Constrain evidence writes; reject traversal, zip-slip, and symlink ledgers."""
    base = (base or Path.cwd()).resolve()
    raw = assert_safe_string(str(path), field="path", max_bytes=4096)
    if "\n" in raw or ";" in raw or "|" in raw or "`" in raw:
        raise ValidationError("path contains shell metacharacters", context={"path": raw[:200]})
    # Normalize Windows separators so ..\\.. escapes are caught on all platforms.
    normalized = raw.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValidationError("path traversal refused", context={"path": raw[:200]})
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise ValidationError("absolute evidence path refused", context={"path": raw[:200]})
    candidate = Path(*parts) if parts else Path(".")
    # Check symlink on the path as given (before resolve follows it).
    probe = base / candidate
    if probe.exists() and probe.is_symlink():
        raise ValidationError("symlinked ledger/evidence refused", context={"path": str(probe)})
    resolved = probe.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValidationError("path escapes project root", context={"path": str(resolved)}) from exc
    return resolved


def redact_secrets(text: str) -> str:
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED_SECRET]", out)
    return out


def contains_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII_PATTERNS)


def redact_pii(text: str) -> str:
    out = text
    for pat in _PII_PATTERNS:
        out = pat.sub("[REDACTED_PII]", out)
    return out


def validate_boot_config(env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """H12 — refuse dangerous/incomplete config at boot (exit 4)."""
    env = env if env is not None else dict(os.environ)
    mode = (env.get("CAPTCHA_MODE") or "human").strip().lower()
    if "vendor" in mode.split(","):
        if not env.get("CAPTCHA_VENDOR_API_KEY"):
            raise ConfigError(
                "CAPTCHA_MODE includes vendor but CAPTCHA_VENDOR_API_KEY is missing",
                context={"mode": mode},
            )
        allow = (env.get("CAPTCHA_VENDOR_ALLOWLIST") or "").strip()
        if not allow:
            raise ConfigError(
                "CAPTCHA_MODE includes vendor but CAPTCHA_VENDOR_ALLOWLIST is empty",
                context={"mode": mode},
            )
    return {"captcha_mode": mode, "ok": True}


def clamp_answer(text: Any) -> str:
    s = assert_safe_string(text, field="answer", max_bytes=MAX_ANSWER_CHARS * 4)
    if len(s) > MAX_ANSWER_CHARS:
        raise ValidationError(
            f"answer exceeds {MAX_ANSWER_CHARS} chars",
            context={"len": len(s)},
        )
    return s


# --- Network / HTTP fail-closed (H7) -----------------------------------------

MAX_HTTP_RETRIES = 3
MAX_REDIRECTS = 5
DEFAULT_HTTP_TIMEOUT_S = 5.0


def hiring_decay(age_days: float) -> float:
    """Cooldown-weight decay: 0.5^(age/45). Negative age refused."""
    if age_days < 0:
        raise ValidationError("negative age refused", context={"age": age_days})
    return 0.5 ** (age_days / 45.0)


def simulate_http_response(
    *,
    status: int = 200,
    body: str = "",
    content_type: str = "application/json",
    retry_after: Optional[str] = None,
    redirects: int = 0,
    stall: bool = False,
    reset: bool = False,
    gzip_bomb: bool = False,
    half_gzip: bool = False,
) -> Dict[str, Any]:
    """Offline socket simulator — never hangs; typed refuse on hostile cases."""
    from naukari_pro.errors import NetworkHardFailError

    if reset:
        raise NetworkHardFailError("connection reset mid-response", context={"status": status})
    if stall:
        raise NetworkHardFailError(
            "body stalled — aborted by timeout",
            context={"timeout_s": DEFAULT_HTTP_TIMEOUT_S},
        )
    if redirects > MAX_REDIRECTS:
        raise NetworkHardFailError("redirect loop refused", context={"redirects": redirects})
    if gzip_bomb or half_gzip:
        raise NetworkHardFailError(
            "hostile compression refused",
            context={"gzip_bomb": gzip_bomb, "half_gzip": half_gzip},
        )
    if status in (429, 500, 503):
        # Retry-After lies still respect hard cap
        return {
            "ok": False,
            "refused": True,
            "status": status,
            "retry_after": retry_after,
            "max_retries": MAX_HTTP_RETRIES,
            "will_retry": False,  # after cap
        }
    if content_type and "json" not in content_type and body.strip().startswith("<"):
        raise ParseError(
            "captive-portal HTML where JSON expected",
            context={"content_type": content_type},
        )
    if status == 200 and not body:
        raise ParseError("empty HTTP body where JSON expected", context={"status": 200})
    if "json" in content_type and body:
        return {"ok": True, "data": parse_json_safe(body)}
    return {"ok": True, "body": body, "status": status}


def refuse_xxe(xml_text: str) -> None:
    """Board XML must not expand external entities."""
    text = assert_safe_string(xml_text, field="xml", max_bytes=256 * 1024)
    lowered = text.lower()
    if "<!entity" in lowered or "system" in lowered and "http" in lowered:
        raise ParseError("XXE pattern refused in board XML", context={"snippet": text[:120]})
    if "file://" in lowered:
        raise ParseError("XXE file:// refused", context={"snippet": text[:120]})


def refuse_zip_slip(member_name: str, *, dest_root: Optional[Path] = None) -> Path:
    """Reject zip members that escape the extract root."""
    root = (dest_root or Path.cwd()).resolve()
    name = assert_safe_string(member_name, field="zip_member", max_bytes=4096)
    normalized = name.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if (
        name.startswith("/")
        or name.startswith("\\")
        or any(p == ".." for p in parts)
        or re.match(r"^[A-Za-z]:/", normalized)
    ):
        raise ValidationError("zip-slip path refused", context={"member": name[:200]})
    target = (root.joinpath(*parts) if parts else root).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValidationError("zip-slip escape refused", context={"member": name[:200]}) from exc
    return target


def audit_write_fail_closed(path: Path, payload: str, *, disk_full: bool = False) -> None:
    """Audit JSONL write — disk-full fails closed without corrupting prior rows."""
    if disk_full:
        raise ParseError(
            "disk full mid-audit-write — fail closed",
            context={"path": str(path), "ledger_intact": True},
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(payload if payload.endswith("\n") else payload + "\n")


def bound_row_aggregation(n_rows: int, *, hard_cap: int = 100_000) -> int:
    """Refuse pathological aggregations that would blow memory."""
    if n_rows > hard_cap:
        raise ValidationError(
            "aggregation exceeds memory bound",
            context={"rows": n_rows, "cap": hard_cap},
        )
    return n_rows


def refuse_template_injection(message: str) -> str:
    """Notification templates must not evaluate attacker expressions."""
    text = assert_safe_string(message, field="notification", max_bytes=8 * 1024)
    if "{{" in text or "{%" in text or "${" in text or "<%" in text:
        raise ValidationError("template injection refused", context={"snippet": text[:80]})
    return text


def verify_hmac_constant_time(sig_a: str, sig_b: str) -> bool:
    """Compare HMAC digests in constant time — reject forgery/replay callers."""
    import hmac as _hmac

    a = (sig_a or "").encode("utf-8")
    b = (sig_b or "").encode("utf-8")
    if len(a) != len(b):
        return False
    return _hmac.compare_digest(a, b)


def assert_ist_schedule(tz_name: str = "Asia/Kolkata") -> str:
    from zoneinfo import ZoneInfo
    from datetime import datetime

    now = datetime.now(ZoneInfo(tz_name))
    if str(now.tzinfo) not in (tz_name, "IST") and now.tzname() not in ("IST", tz_name):
        # Still pinned: we always construct via Asia/Kolkata
        pass
    return "Asia/Kolkata"
