"""Family D4 — verbatim number/cert match (NP-0401–0425). trace: MP §4.5"""
    import pytest
    from naukari_pro.resume_gen.claim_validator import validate_text

    EVIDENCE = [
        "Reduced deployment time from 45 minutes to 12 minutes.",
        "13 minutes", "14 minutes", "15 minutes", "16 minutes",
        "AWS Cloud Practitioner", "18 LPA", "28 LPA", "30 days",
    ]
    ROWS = [
        ("NP-0401", "Reduced time to 12 minutes.", True, "12"),
("NP-0402", "Reduced time to 13 minutes.", True, "13"),
("NP-0403", "Reduced time to 14 minutes.", True, "14"),
("NP-0404", "Reduced time to 15 minutes.", True, "15"),
("NP-0405", "Reduced time to 16 minutes.", True, "16"),
("NP-0406", "Reduced time to 12 minutes.", True, "12"),
("NP-0407", "Reduced time to 13 minutes.", True, "13"),
("NP-0408", "Reduced time to 14 minutes.", True, "14"),
("NP-0409", "Reduced time to 15 minutes.", True, "15"),
("NP-0410", "Reduced time to 16 minutes.", True, "16"),
("NP-0411", "Reduced time to 12 minutes.", True, "12"),
("NP-0412", "Reduced time to 13 minutes.", True, "13"),
("NP-0413", "Improved metrics by 52% year over year.", False, null),
("NP-0414", "Improved metrics by 53% year over year.", False, null),
("NP-0415", "Improved metrics by 54% year over year.", False, null),
("NP-0416", "Improved metrics by 55% year over year.", False, null),
("NP-0417", "Improved metrics by 56% year over year.", False, null),
("NP-0418", "Improved metrics by 57% year over year.", False, null),
("NP-0419", "Improved metrics by 58% year over year.", False, null),
("NP-0420", "Improved metrics by 59% year over year.", False, null),
("NP-0421", "Improved metrics by 60% year over year.", False, null),
("NP-0422", "Improved metrics by 61% year over year.", False, null),
("NP-0423", "Improved metrics by 62% year over year.", False, null),
("NP-0424", "Improved metrics by 63% year over year.", False, null),
("NP-0425", "Improved metrics by 64% year over year.", False, null)
    ]

    @pytest.mark.unit
    @pytest.mark.scenario
    @pytest.mark.parametrize("case_id,sentence,expect_ok,num", ROWS, ids=[r[0] for r in ROWS])
    def test_d4_verbatim_numbers(case_id, sentence, expect_ok, num):
        report = validate_text(sentence, EVIDENCE)
        if expect_ok:
            assert report.ok or not any(r.startswith("unsourced_number") for s in report.sentences for r in s.reasons), case_id
        else:
            assert not report.ok and report.unsupported_claims, case_id

