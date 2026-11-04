"""OpenAPI tool mirror + HMAC webhook emit (offline)."""

from __future__ import annotations

import json

import pytest

from naukari_pro.api.app import create_api_app, verify_webhook_signature
from naukari_pro.mcp.server import handle_tool


def test_api_health_and_apply_dry_run():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    app = create_api_app()
    client = TestClient(app)
    assert client.get("/health").json()["ok"] is True
    tools = client.get("/tools").json()["tools"]
    assert len(tools) >= 10
    r = client.post("/v1/tools/apply_job", json={"job_key": "greenhouse:1"})
    assert r.status_code == 200
    assert r.json()["dry_run"] is True


def test_webhook_hmac_roundtrip(monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    monkeypatch.setenv("NAUKARI_WEBHOOK_SECRET", "test-secret")
    app = create_api_app()
    client = TestClient(app)
    sub = client.post(
        "/v1/webhooks/subscribe",
        json={"url": "https://example.invalid/hook", "events": ["job.found"]},
    )
    assert sub.json()["ok"] is True
    payload = {"event": "job.found", "job_key": "ashby:1"}
    emitted = client.post("/v1/webhooks/emit", json=payload).json()
    assert emitted["signature"]
    assert emitted["deliveries"]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert verify_webhook_signature(raw, emitted["signature"], "test-secret")


def test_e2e_offline_pipeline_chain():
    """job → score → tailor → draft → dry-run apply → submit blocked without approval."""
    scored = handle_tool(
        "score_job",
        {"job_key": "missing-key-for-offline"},
    )
    # missing job returns error — seed via tailor/draft/apply path instead
    tailored = handle_tool("tailor_resume", {"job_key": "demo", "jd_text": "DevOps Kubernetes"})
    assert tailored.get("dry_artifact") is True
    answers = handle_tool(
        "draft_answers",
        {"job_key": "demo", "questions": ["Notice period?"]},
    )
    assert answers["answers"][0]["status"] == "ASK_USER"
    dry = handle_tool("apply_job", {"job_key": "demo"})
    assert dry["dry_run"] is True
    blocked = handle_tool("apply_job", {"job_key": "demo", "dry_run": False})
    assert blocked["exit_code"] == 2
    rejected = handle_tool("approve_submission", {"approval_token": "short"})
    assert rejected["status"] == "rejected"
