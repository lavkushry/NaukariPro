"""Family D2 — novelty-ratio ≤ 0.34 cap (NP-0361–0380). trace: MP §4.5"""
import pytest
from naukari_pro.resume_gen.claim_validator import validate_text, novelty_ratio

EVIDENCE = "DevOps Engineer with Kubernetes Docker Terraform AWS. Reduced deployment time from 45 minutes to 12 minutes. AWS Cloud Practitioner. Notice period 30 days. Current CTC 18 LPA. Expected CTC 28 LPA. Containerized 8 microservices on EKS with Helm."
ROWS = [
    ("NP-0361", "Kubernetes Docker Terraform AWS.", True),
("NP-0362", "Reduced deployment time from 45 minutes to 12 minutes.", True),
("NP-0363", "AWS Cloud Practitioner. Notice period 30 days.", True),
("NP-0364", "Current CTC 18 LPA. Expected CTC 28 LPA.", True),
("NP-0365", "Containerized 8 microservices on EKS with Helm.", True),
("NP-0366", "DevOps Engineer with Kubernetes Docker Terraform AWS.", True),
("NP-0367", "Reduced deployment time from 45 minutes to 12 minutes.", True),
("NP-0368", "AWS Cloud Practitioner. Notice period 30 days.", True),
("NP-0369", "My holistic approach unlocked unprecedented stakeholder value across the tapestry.", False),
("NP-0370", "I fostered a culture of excellence driving impactful paradigm shifts daily.", False),
("NP-0371", "I orchestrated a world-class synergy of container orchestration paradigms across polyglot estates.", False),
("NP-0372", "Leveraging cutting-edge methodologies I revolutionized delivery velocity exponentially.", False),
("NP-0373", "As a passionate results-driven professional I spearheaded transformational initiatives.", False),
("NP-0374", "My holistic approach unlocked unprecedented stakeholder value across the tapestry.", False),
("NP-0375", "I fostered a culture of excellence driving impactful paradigm shifts daily. synergistic excellence", False),
("NP-0376", "I orchestrated a world-class synergy of container orchestration paradigms across polyglot estates. synergistic excellence", False),
("NP-0377", "Leveraging cutting-edge methodologies I revolutionized delivery velocity exponentially. synergistic excellence", False),
("NP-0378", "As a passionate results-driven professional I spearheaded transformational initiatives. synergistic excellence", False),
("NP-0379", "My holistic approach unlocked unprecedented stakeholder value across the tapestry. synergistic excellence", False),
("NP-0380", "I fostered a culture of excellence driving impactful paradigm shifts daily. synergistic excellence", False)
]

@pytest.mark.unit
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,text,expect_ok", ROWS, ids=[r[0] for r in ROWS])
def test_d2_novelty_cap(case_id, text, expect_ok):
    report = validate_text(text, [EVIDENCE])
    ratio = report.novelty_ratio
    if expect_ok:
        assert report.ok and ratio <= 0.34, f"{case_id} ratio={ratio} claims={report.unsupported_claims}"
    else:
        assert (not report.ok) or ratio > 0.34, f"{case_id} should reject ratio={ratio}"

