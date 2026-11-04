"""Family D3 — PUFFERY regex (NP-0381–0400). trace: MP §4.5"""
    import pytest
    from naukari_pro.resume_gen.claim_validator import PUFFERY, validate_text

    ROWS = [
        ("NP-0381", "world-class"),
("NP-0382", "rockstar ninja"),
("NP-0383", "10x engineer"),
("NP-0384", "best-in-class"),
("NP-0385", "cutting-edge"),
("NP-0386", "proven track record"),
("NP-0387", "highly skilled"),
("NP-0388", "passionate"),
("NP-0389", "synergy"),
("NP-0390", "robust solution"),
("NP-0391", "spearheaded transformational"),
("NP-0392", "effective leader"),
("NP-0393", "crucial expert"),
("NP-0394", "fostered excellence"),
("NP-0395", "leveraged synergies"),
("NP-0396", "game-changer"),
("NP-0397", "visionary genius"),
("NP-0398", "elite performer"),
("NP-0399", "unparalleled mastery"),
("NP-0400", "legendary coder")
    ]

    @pytest.mark.redteam
    @pytest.mark.scenario
    @pytest.mark.parametrize("case_id,phrase", ROWS, ids=[r[0] for r in ROWS])
    def test_d3_puffery(case_id, phrase):
        sentence = f"I am a {phrase} DevOps engineer delivering results."
        # Either regex hits OR validate_text rejects unsupported puffery
        hit = bool(PUFFERY.search(sentence)) or bool(PUFFERY.search(phrase))
        report = validate_text(sentence, ["DevOps engineer kubernetes"])
        assert hit or (not report.ok and report.unsupported_claims), case_id

