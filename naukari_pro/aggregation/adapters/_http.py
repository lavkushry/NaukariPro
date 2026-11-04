"""Shared async HTTP helpers for adapters (stdlib + optional aiohttp)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


def sync_request(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: float = 30.0,
) -> Tuple[int, Dict[str, str], bytes]:
    req = urllib.request.Request(url, data=body, method=method.upper())
    hdrs = {
        "User-Agent": "NaukariProAggregator/1.0 (+https://github.com/local/naukari_pro)",
        "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
    }
    if headers:
        hdrs.update(headers)
    for k, v in hdrs.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        data = e.read() if hasattr(e, "read") else b""
        return int(e.code), dict(getattr(e, "headers", {}) or {}), data


async def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Tuple[int, Any]:
    import asyncio

    body = None
    hdrs = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    def _do() -> Tuple[int, Any]:
        code, _hdr, raw = sync_request(
            url, method=method, headers=hdrs, body=body, timeout=timeout
        )
        if not raw:
            return code, None
        try:
            return code, json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return code, raw.decode("utf-8", errors="replace")

    return await asyncio.to_thread(_do)


async def http_text(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Tuple[int, str]:
    import asyncio

    def _do() -> Tuple[int, str]:
        code, _hdr, raw = sync_request(
            url, method=method, headers=headers, timeout=timeout
        )
        return code, raw.decode("utf-8", errors="replace")

    return await asyncio.to_thread(_do)
