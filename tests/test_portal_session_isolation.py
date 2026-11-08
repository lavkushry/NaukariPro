"""Portal fills must never contend for the Naukri Chromium session lock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from naukari_pro.config import SESSION_DIR
from naukari_pro.modules.career_portals import PORTALS_SESSION_DIR, CareerPortalFiller


def test_portals_session_dir_is_isolated_from_naukri():
    assert PORTALS_SESSION_DIR != SESSION_DIR
    assert "career_portals_system" in PORTALS_SESSION_DIR
    assert "naukri_system" in SESSION_DIR


def test_fill_passes_portals_session_dir_to_stealth_context():
    filler = CareerPortalFiller()
    captured = {}

    class _Ctx:
        pages = []

        def new_page(self):
            return MagicMock()

        def close(self):
            return None

    def fake_stealth(p, headless=False, session_dir=None, lock_timeout=15.0, **kwargs):
        captured["session_dir"] = session_dir
        captured["lock_timeout"] = lock_timeout
        return _Ctx()

    with patch("naukari_pro.modules.career_portals._is_asyncio_loop_running", return_value=False), patch(
        "naukari_pro.modules.role_guard.is_strictly_data_or_cloud_role",
        return_value=(True, "ok"),
    ), patch(
        "naukari_pro.modules.db.is_job_already_applied",
        return_value=False,
    ), patch(
        "playwright.sync_api.sync_playwright",
    ) as sp, patch(
        "naukari_pro.session.get_stealth_context",
        side_effect=fake_stealth,
    ), patch.object(
        CareerPortalFiller,
        "fill_in_playwright",
        return_value=(True, ["email"]),
    ):
        mgr = MagicMock()
        mgr.__enter__ = MagicMock(return_value=mgr)
        mgr.__exit__ = MagicMock(return_value=False)
        sp.return_value = mgr
        filler.fill(
            portal_url="https://boards.greenhouse.io/acme/jobs/1",
            company="Acme",
            role="Azure Data Engineer",
            headless=True,
        )

    assert captured.get("session_dir") == PORTALS_SESSION_DIR
    assert captured.get("lock_timeout", 0) >= 60
