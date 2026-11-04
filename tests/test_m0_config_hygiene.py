"""M0: no hardcoded personal credentials in config loader / examples."""

from __future__ import annotations

from pathlib import Path

import naukari_pro.config as cfg


ROOT = Path(__file__).resolve().parents[1]


def test_config_py_has_no_hardcoded_gmail():
    text = (ROOT / "naukari_pro" / "config.py").read_text(encoding="utf-8")
    assert "lav84095@gmail.com" not in text


def test_env_example_uses_placeholders():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "lav84095@gmail.com" not in text
    assert "you@example.com" in text or "CANDIDATE_EMAIL=" in text
    assert "AI_GATEWAY_DEFAULT_PROVIDER" in text


def test_tracked_config_json_scrubbed_identity():
    import json

    data = json.loads((ROOT / "naukri_system" / "config.json").read_text(encoding="utf-8"))
    cand = data.get("candidate") or {}
    assert not cand.get("email")
    assert not cand.get("phone")
    assert "lav84095" not in str(cand.get("email") or "")


def test_load_config_overlays_candidate_env(monkeypatch):
    monkeypatch.setenv("CANDIDATE_EMAIL", "ci@example.com")
    monkeypatch.setenv("CANDIDATE_PHONE", "+91-1111111111")
    monkeypatch.setenv("CANDIDATE_NAME", "CI Candidate")
    loaded = cfg.load_config()
    assert loaded["candidate"]["email"] == "ci@example.com"
    assert loaded["candidate"]["phone"] == "+91-1111111111"
    assert loaded["candidate"]["name"] == "CI Candidate"
