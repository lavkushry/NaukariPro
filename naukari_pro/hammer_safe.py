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


def _is_blocked_ssrf_host(host: str) -> bool:
    h = (host or "").lower().strip(".")
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
    # Decimal / IPv4 forms
    try:
        import ipaddress

        ip = ipaddress.ip_address(h)
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_private
            or ip.is_reserved
            or ip.is_multicast
        ):
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
            import ipaddress

            ip = ipaddress.ip_address(int(h))
            if ip.is_loopback or ip.is_private or ip.is_link_local:
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
    candidate = Path(raw)
    # Check symlink on the path as given (before resolve follows it).
    probe = candidate if candidate.is_absolute() else (base / candidate)
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
