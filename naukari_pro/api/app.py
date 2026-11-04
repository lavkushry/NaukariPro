"""
FastAPI OpenAPI 3.1 app — every MCP tool as an HTTP endpoint.
API-key auth via NAUKARI_API_KEY (required unless NAUKARI_API_DEV_OPEN=1).
"""

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional

from naukari_pro.hammer_safe import redact_pii, redact_secrets
from naukari_pro.mcp.server import TOOLS, handle_tool, list_tools


def create_api_app():
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException, Request
    except ImportError as exc:
        raise RuntimeError("fastapi required for REST API") from exc

    app = FastAPI(
        title="NaukariPro API",
        version="2.0.0",
        description="OpenAPI mirror of naukari-pro-mcp tools. dry_run defaults true on apply.",
    )

    api_key_env = os.environ.get("NAUKARI_API_KEY", "")
    webhook_secret = os.environ.get("NAUKARI_WEBHOOK_SECRET", "")
    dev_open = (os.environ.get("NAUKARI_API_DEV_OPEN") or "").strip() in ("1", "true", "yes")

    def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
        # Fail closed: unset key refuses tool/webhook routes unless explicit dev open.
        if not api_key_env:
            if dev_open:
                return
            raise HTTPException(
                status_code=401,
                detail="NAUKARI_API_KEY required (or set NAUKARI_API_DEV_OPEN=1 for local-only)",
            )
        if not x_api_key or not hmac.compare_digest(x_api_key, api_key_env):
            raise HTTPException(status_code=401, detail="invalid api key")

    app.state.webhooks = []
    app.state.event_log = []

    @app.get("/health")
    def health():
        return {"ok": True, "service": "naukari-pro-api", "version": "2.0.0"}

    @app.get("/tools", dependencies=[Depends(require_api_key)])
    def tools():
        return {"tools": list_tools()}

    @app.get("/openapi-tools.json", dependencies=[Depends(require_api_key)])
    def openapi_tools():
        return {
            "openapi": "3.1.0",
            "info": {"title": "NaukariPro MCP Tools", "version": "2.0.0"},
            "paths": {
                f"/v1/tools/{t.name}": {
                    "post": {
                        "summary": t.description,
                        "requestBody": {
                            "content": {
                                "application/json": {"schema": t.input_schema}
                            }
                        },
                    }
                }
                for t in TOOLS
            },
        }

    @app.post("/v1/tools/{tool_name}", dependencies=[Depends(require_api_key)])
    async def call_tool(tool_name: str, request: Request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        return handle_tool(tool_name, data)

    @app.post("/v1/webhooks/subscribe", dependencies=[Depends(require_api_key)])
    async def subscribe(request: Request):
        data = await request.json()
        entry = {
            "url": str(data.get("url") or ""),
            "events": list(data.get("events") or ["job.found", "application.submitted"]),
            "secret": data.get("secret") or webhook_secret or "dev-secret",
            "created_at": time.time(),
        }
        if not entry["url"]:
            raise HTTPException(status_code=400, detail="url required")
        app.state.webhooks.append(entry)
        return {"ok": True, "subscriptions": len(app.state.webhooks)}

    @app.post("/v1/webhooks/emit", dependencies=[Depends(require_api_key)])
    async def emit_event(request: Request):
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {}
        # Redact PII/secrets before ledger persistence (Phase-5 F5).
        safe_payload = json.loads(
            redact_pii(redact_secrets(json.dumps(payload, ensure_ascii=False)))
        )
        if not isinstance(safe_payload, dict):
            safe_payload = {"redacted": True}
        event = str(safe_payload.get("event") or payload.get("event") or "error.blocked")
        raw = json.dumps(safe_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        secret = (webhook_secret or "dev-secret").encode("utf-8")
        sig = hmac.new(secret, raw, hashlib.sha256).hexdigest()
        record = {
            "event": event,
            "payload": safe_payload,
            "signature": sig,
            "ts": time.time(),
            "deliveries": [],
        }
        for sub in list(app.state.webhooks):
            if event in sub.get("events", []):
                record["deliveries"].append(
                    {
                        "url": sub["url"],
                        "status": "queued",
                        "signature_header": f"sha256={sig}",
                    }
                )
        app.state.event_log.append(record)
        return record

    @app.get("/v1/webhooks/log", dependencies=[Depends(require_api_key)])
    def webhook_log():
        return {"events": list(app.state.event_log)}

    return app


def verify_webhook_signature(body: bytes, signature_header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    got = (signature_header or "").replace("sha256=", "").strip()
    return hmac.compare_digest(expected, got)
