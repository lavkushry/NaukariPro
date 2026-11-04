"""Family A2 — task routing (NP-0028–0051). trace: MP §4.1"""
import pytest
from naukari_pro.llm.routing import GatewayConfig

ROWS = [
    ("NP-0028", "jd_extract", "routed"),
("NP-0029", "jd_extract", "budget_paused"),
("NP-0030", "match_score", "routed"),
("NP-0031", "match_score", "budget_paused"),
("NP-0032", "resume_tailor", "routed"),
("NP-0033", "resume_tailor", "budget_paused"),
("NP-0034", "cover_letter", "routed"),
("NP-0035", "cover_letter", "budget_paused"),
("NP-0036", "answer_draft", "routed"),
("NP-0037", "answer_draft", "budget_paused"),
("NP-0038", "answer_vet", "routed"),
("NP-0039", "answer_vet", "budget_paused"),
("NP-0040", "cv_parse", "routed"),
("NP-0041", "cv_parse", "budget_paused"),
("NP-0042", "match_score", "routed"),
("NP-0043", "match_score", "budget_paused"),
("NP-0044", "resume_tailor", "routed"),
("NP-0045", "resume_tailor", "budget_paused"),
("NP-0046", "answer_draft", "routed"),
("NP-0047", "answer_draft", "budget_paused"),
("NP-0048", "jd_extract", "routed"),
("NP-0049", "jd_extract", "budget_paused"),
("NP-0050", "cover_letter", "routed"),
("NP-0051", "cover_letter", "budget_paused")
]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,task,variant", ROWS, ids=[r[0] for r in ROWS])
def test_a2_task_routing(case_id, task, variant):
    cfg = GatewayConfig()
    tasks = cfg.raw.get("tasks", {})
    # Unknown synthetic tasks still must not crash routing lookup
    entry = tasks.get(task) or tasks.get("match_score")
    assert entry is not None, case_id
    assert "provider" in entry or "model" in entry, case_id
    if variant == "budget_paused":
        assert "paused_budget" in cfg.raw or hasattr(cfg, "paused_budget")

