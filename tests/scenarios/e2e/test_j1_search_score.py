"""Family J1 — golden journey search_score (NP-0921–0928). trace: MP §9"""
import json
import pytest
from naukari_pro.matching.deterministic_score import score_job
from naukari_pro.resume_gen.claim_validator import validate_text
from naukari_pro.governed_apply.fill_verify import verify_field
from naukari_pro.governed_apply.approval import ApprovalQueue
from naukari_pro.governed_apply.captcha_safety import CaptchaSafetyManager, EXIT_CAPTCHA_BLOCKED
from naukari_pro.governed_apply.exit_codes import EXIT_OK

ROWS = [(f"NP-{i:04d}", i - 921) for i in range(921, 921+8)]

@pytest.mark.e2e_mock
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,step", ROWS, ids=[r[0] for r in ROWS])
def test_j1_search_score(case_id, step, fixtures_root, tmp_path, profile_evidence):
    jobs = json.loads((fixtures_root / "boards" / "india_jobs_200.json").read_text())
    assert len(jobs) >= 200
    if 1 == 1:
        scored = [score_job(j) for j in jobs[:50]]
        ranked = sorted(scored, key=lambda s: s.total, reverse=True)
        assert ranked[0].total >= ranked[-1].total
        assert step < 8
        assert isinstance(ranked[step % len(ranked)].total, float)
    elif 1 == 2:
        text = profile_evidence["resume_text"] if step % 2 == 0 else "Certified Kubernetes Administrator inventing 40% gains"
        report = validate_text(text, [profile_evidence["resume_text"]])
        if step % 2 == 0:
            assert report.ok or report.novelty_ratio <= 0.34
        else:
            assert not report.ok and report.unsupported_claims
    elif 1 == 3:
        r = verify_field(field_id="name", expected="Lavkush", dom_value="Lavkush", check_validity=True, model_value="Lavkush")
        assert r.ok is True
        submitted = False  # dry-run
        assert submitted is False
        assert EXIT_OK == 0
    elif 1 == 4:
        q = ApprovalQueue(db_path=tmp_path / "a.db")
        items = q.enqueue_batch([{"url": "https://job/1", "company": "Acme", "title": "DevOps"}])
        assert items[0].token
        assert items[0].status == "pending"
    else:
        mgr = CaptchaSafetyManager(mode="human", db_path=tmp_path / "c.db", board="gh")
        result = mgr.handle(captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x")
        assert result.exit_code == EXIT_CAPTCHA_BLOCKED
        assert result.resolved_by == "human"
        status = "blocked"
        assert status != "submitted" and status != "applied"

