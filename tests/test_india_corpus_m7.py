"""M7: India form corpus manifest + field inventory (offline)."""

from __future__ import annotations

import json
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "naukari_pro" / "fixtures" / "india_forms"


def test_india_manifest_and_fixtures_exist():
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenarios"]
    for sc in manifest["scenarios"]:
        html_path = CORPUS / sc["html_fixture"]
        assert html_path.exists(), sc["html_fixture"]
        html = html_path.read_text(encoding="utf-8")
        for field in sc["expected_fields"]:
            assert re.search(rf'name=["\']{re.escape(field)}["\']', html), field


def test_workday_india_marks_absolute_blockers():
    html = (CORPUS / "workday_india_notice.html").read_text(encoding="utf-8")
    assert 'data-blocker="government_id"' in html
    assert "aadhaar" in html.lower()
    assert "pan" in html.lower()
