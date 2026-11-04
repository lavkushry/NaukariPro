"""M6: screen-pass north-star metric segmentation."""

from __future__ import annotations

from naukari_pro.tracking.models import ApplicationStatus
from naukari_pro.tracking.store import TrackingStore


def test_screen_pass_rate_segmented(tmp_path):
    store = TrackingStore(db_path=tmp_path / "t.db")
    a = store.upsert_application(
        {"url": "https://x/1", "company": "A", "title": "DE", "ats": "greenhouse", "fit_score": 80},
        status=ApplicationStatus.APPLIED.value,
    )
    b = store.upsert_application(
        {"url": "https://x/2", "company": "B", "title": "DE", "ats": "ashby", "fit_score": 85},
        status=ApplicationStatus.APPLIED.value,
    )
    store.set_status(b, ApplicationStatus.SCREENING.value)

    with store._connect() as conn:
        conn.execute(
            "UPDATE applications SET resume_version=?, answer_template=? WHERE id=?",
            ("v_platform", "india_default", a),
        )
        conn.execute(
            "UPDATE applications SET resume_version=?, answer_template=? WHERE id=?",
            ("v_platform", "india_default", b),
        )

    spr = store.screen_pass_rate()
    assert spr["submitted"] == 2
    assert spr["screens"] == 1
    assert spr["rate"] == 0.5
    assert "greenhouse" in spr["by_board"]
    assert spr["by_resume_version"]["v_platform"]["screens"] == 1
