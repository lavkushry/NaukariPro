"""Family D1 — sentence-support ≥ 0.25 boundary (NP-0341–0360). trace: MP §4.5"""
    import pytest
    from naukari_pro.resume_gen.claim_validator import validate_text, sentence_support

    ROWS = [
        ("NP-0341", "Kubernetes Docker Terraform", "Kubernetes Docker Terraform AWS", True),
("NP-0342", "xyzzy plugh foo bar baz qux", "unrelated evidence blob here", False),
("NP-0343", "Reduced deployment time", "Reduced deployment time from 45 minutes", True),
("NP-0344", "Certified Kubernetes Administrator expert", "AWS Cloud Practitioner only", False),
("NP-0345", "Docker", "Docker", True),
("NP-0346", "alpha beta gamma delta", "nothing matching tokens here", False),
("NP-0347", "Prometheus Grafana SLOs", "Prometheus Grafana SLOs at 99.5", True),
("NP-0348", "fabricated forty percent improvement", "no such metric in evidence", False),
("NP-0349", "Notice period 30 days", "Notice period 30 days Current CTC", True),
("NP-0350", "world class rockstar ninja", "plain devops work", False),
("NP-0351", "EKS with Helm", "Containerized microservices on EKS with Helm", True),
("NP-0352", "quantum blockchain visionary", "kubernetes docker", False),
("NP-0353", "AWS Cloud Practitioner", "AWS Cloud Practitioner certificate", True),
("NP-0354", "PhD in underwater basket weaving", "AWS Cloud Practitioner", False),
("NP-0355", "18 LPA current", "Current CTC 18 LPA Expected", True),
("NP-0356", "saved five million dollars", "18 LPA 28 LPA", False),
("NP-0357", "Terraform AWS", "Kubernetes Docker Terraform AWS", True),
("NP-0358", "invented ISO27001 lead auditor", "no iso cert listed", False),
("NP-0359", "12 minutes deploy", "from 45 minutes to 12 minutes", True),
("NP-0360", "led fifty person org", "individual contributor devops", False)
    ]

    @pytest.mark.unit
    @pytest.mark.scenario
    @pytest.mark.parametrize("case_id,sentence,evidence,expect_ok", ROWS, ids=[r[0] for r in ROWS])
    def test_d1_sentence_support(case_id, sentence, evidence, expect_ok):
        support = sentence_support(sentence, evidence)
        report = validate_text(sentence, [evidence], drop_ungrounded=False)
        if expect_ok:
            assert support >= 0.25, f"{case_id} support={support}"
            assert report.ok or all(s.support >= 0.25 for s in report.sentences if s.sentence), case_id
        else:
            assert support < 0.25 or (not report.ok and report.unsupported_claims), (
                f"{case_id} expected reject support={support} ok={report.ok}"
            )

