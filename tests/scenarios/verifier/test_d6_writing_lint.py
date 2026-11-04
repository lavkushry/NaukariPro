"""Family D6 — writing lint banned phrases (NP-0441–0470). trace: MP §4.5"""
import pytest
from naukari_pro.resume_gen.writing_lint import lint_text, BANNED_PHRASES

ROWS = [
    ("NP-0441", "as an ai"),
("NP-0442", "in today's fast-paced"),
("NP-0443", "delve into"),
("NP-0444", "tapestry"),
("NP-0445", "multifaceted"),
("NP-0446", "leverage synergies"),
("NP-0447", "seamless integration"),
("NP-0448", "cutting-edge"),
("NP-0449", "game-changer"),
("NP-0450", "passionate about"),
("NP-0451", "thrilled to"),
("NP-0452", "excited to apply"),
("NP-0453", "perfect fit"),
("NP-0454", "hit the ground running"),
("NP-0455", "synergistic"),
("NP-0456", "holistic approach"),
("NP-0457", "paradigm shift"),
("NP-0458", "keen eye for detail"),
("NP-0459", "think outside the box"),
("NP-0460", "move the needle"),
("NP-0461", "circle back"),
("NP-0462", "low-hanging fruit"),
("NP-0463", "at the end of the day"),
("NP-0464", "going forward"),
("NP-0465", "first and foremost"),
("NP-0466", "needless to say"),
("NP-0467", "very unique"),
("NP-0468", "results-driven professional"),
("NP-0469", "self-starter with"),
("NP-0470", "team player who")
]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,phrase", ROWS, ids=[r[0] for r in ROWS])
def test_d6_writing_lint(case_id, phrase):
    assert any(phrase in b for b in BANNED_PHRASES) or phrase in BANNED_PHRASES, case_id
    verdict = lint_text(f"Dear team, {phrase} I deliver value.")
    assert verdict.verdict in ("REWRITE", "DO NOT SEND", "PASS"), case_id
    assert verdict.verdict != "PASS" or phrase not in f"Dear team, {phrase} I deliver value.".lower()
    # Prefer reject/rewrite for banned content
    assert verdict.verdict in ("REWRITE", "DO NOT SEND"), f"{case_id} verdict={verdict.verdict}"

