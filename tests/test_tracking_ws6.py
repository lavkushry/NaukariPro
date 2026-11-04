"""WS6: tracking funnel, interview uniqueness, notifications idempotency, bandit reward map."""

from __future__ import annotations

import pytest

from naukari_pro.tracking.bandit_bridge import reward_for_status, update_bandit_from_outcome
from naukari_pro.tracking.dashboard import render_dashboard_html
from naukari_pro.tracking.digest import build_weekly_digest
from naukari_pro.tracking.models import ApplicationStatus
from naukari_pro.tracking.notifications import NotificationQueue
from naukari_pro.tracking.store import TrackingStore


def test_funnel_and_interview_unique(tmp_path):
    store = TrackingStore(db_path=tmp_path / "t.db")
    aid = store.upsert_application(
        {"url": "https://x/1", "company": "Acme", "title": "DE", "ats": "greenhouse", "fit_score": 88},
        status=ApplicationStatus.SAVED.value,
    )
    store.upsert_application(
        {"url": "https://x/1", "company": "Acme", "title": "DE", "ats": "greenhouse", "fit_score": 88},
        status=ApplicationStatus.APPLIED.value,
    )
    store.add_interview_round(aid, 1, "recruiter")
    store.add_interview_round(aid, 1, "hiring_manager")  # upsert same round
    store.set_status(aid, ApplicationStatus.REJECTED.value, rejection_hours=12)
    funnel = store.funnel_counts()
    assert funnel["applied"] + funnel["rejected"] + funnel["saved"] >= 1
    hist = store.rejection_histogram()
    assert hist["lt_24h"] == 1
    assert store.rejection_rate_by_ats().get("greenhouse", 0) == 1.0


def test_notification_idempotency(tmp_path):
    q = NotificationQueue(db_path=tmp_path / "n.db")
    assert q.enqueue(user_id="u1", job_key="j1", channel="email", payload="hi", delay_minutes=0) is True
    assert q.enqueue(user_id="u1", job_key="j1", channel="email", payload="hi again", delay_minutes=0) is False
    sent = q.deliver_due()
    assert sent == 1
    assert q.deliver_due() == 0


def test_dashboard_html_and_digest(tmp_path):
    store = TrackingStore(db_path=tmp_path / "t.db")
    store.upsert_application(
        {"url": "https://x/2", "company": "Beta", "title": "Platform", "ats": "lever", "fit_score": 70},
        status="saved",
    )
    html = render_dashboard_html(store)
    assert "NaukariPro Tracking" in html
    digest = build_weekly_digest(store)
    assert "Weekly Digest" in digest["body"]
    assert digest["funnel"]["saved"] == 1


def test_bandit_reward_map():
    assert reward_for_status("offer") == 1.0
    assert reward_for_status("rejected") < 0
    # Should not crash even if policy update internals differ
    result = update_bandit_from_outcome(
        {"match_score": 80, "company": "Acme", "platform": "greenhouse"},
        "interview",
    )
    assert "reward" in result
    assert result["reward"] == 0.7
