"""Family E1 — form-fill matrix 5×10×2 (NP-0491–0590). trace: MP §4.6"""
import pytest
from pathlib import Path
from naukari_pro.governed_apply.fill_verify import verify_field

PROFILE = {
    "text": "Lavkush Kumar",
    "email": "candidate@example.com",
    "phone": "+919876543210",
    "select-dropdown": "India",
    "multi-select": "Python",
    "date": "2026-07-01",
    "file-upload": "resume.pdf",
    "textarea": "DevOps engineer with Kubernetes experience.",
    "radio": "yes",
    "checkbox": "true",
}
EDGE = {
    "text": "  Lavkush\\u200b Kumar 🚀 ",
    "email": "not-an-email",
    "phone": "000",
    "select-dropdown": "",
    "multi-select": "",
    "date": "not-a-date",
    "file-upload": "",
    "textarea": "x" * 5000,
    "radio": "",
    "checkbox": "false",
}
ROWS = [
    ("NP-0491", "greenhouse", "text", "valid"),
("NP-0492", "greenhouse", "text", "edge"),
("NP-0493", "greenhouse", "email", "valid"),
("NP-0494", "greenhouse", "email", "edge"),
("NP-0495", "greenhouse", "phone", "valid"),
("NP-0496", "greenhouse", "phone", "edge"),
("NP-0497", "greenhouse", "select-dropdown", "valid"),
("NP-0498", "greenhouse", "select-dropdown", "edge"),
("NP-0499", "greenhouse", "multi-select", "valid"),
("NP-0500", "greenhouse", "multi-select", "edge"),
("NP-0501", "greenhouse", "date", "valid"),
("NP-0502", "greenhouse", "date", "edge"),
("NP-0503", "greenhouse", "file-upload", "valid"),
("NP-0504", "greenhouse", "file-upload", "edge"),
("NP-0505", "greenhouse", "textarea", "valid"),
("NP-0506", "greenhouse", "textarea", "edge"),
("NP-0507", "greenhouse", "radio", "valid"),
("NP-0508", "greenhouse", "radio", "edge"),
("NP-0509", "greenhouse", "checkbox", "valid"),
("NP-0510", "greenhouse", "checkbox", "edge"),
("NP-0511", "ashby", "text", "valid"),
("NP-0512", "ashby", "text", "edge"),
("NP-0513", "ashby", "email", "valid"),
("NP-0514", "ashby", "email", "edge"),
("NP-0515", "ashby", "phone", "valid"),
("NP-0516", "ashby", "phone", "edge"),
("NP-0517", "ashby", "select-dropdown", "valid"),
("NP-0518", "ashby", "select-dropdown", "edge"),
("NP-0519", "ashby", "multi-select", "valid"),
("NP-0520", "ashby", "multi-select", "edge"),
("NP-0521", "ashby", "date", "valid"),
("NP-0522", "ashby", "date", "edge"),
("NP-0523", "ashby", "file-upload", "valid"),
("NP-0524", "ashby", "file-upload", "edge"),
("NP-0525", "ashby", "textarea", "valid"),
("NP-0526", "ashby", "textarea", "edge"),
("NP-0527", "ashby", "radio", "valid"),
("NP-0528", "ashby", "radio", "edge"),
("NP-0529", "ashby", "checkbox", "valid"),
("NP-0530", "ashby", "checkbox", "edge"),
("NP-0531", "lever", "text", "valid"),
("NP-0532", "lever", "text", "edge"),
("NP-0533", "lever", "email", "valid"),
("NP-0534", "lever", "email", "edge"),
("NP-0535", "lever", "phone", "valid"),
("NP-0536", "lever", "phone", "edge"),
("NP-0537", "lever", "select-dropdown", "valid"),
("NP-0538", "lever", "select-dropdown", "edge"),
("NP-0539", "lever", "multi-select", "valid"),
("NP-0540", "lever", "multi-select", "edge"),
("NP-0541", "lever", "date", "valid"),
("NP-0542", "lever", "date", "edge"),
("NP-0543", "lever", "file-upload", "valid"),
("NP-0544", "lever", "file-upload", "edge"),
("NP-0545", "lever", "textarea", "valid"),
("NP-0546", "lever", "textarea", "edge"),
("NP-0547", "lever", "radio", "valid"),
("NP-0548", "lever", "radio", "edge"),
("NP-0549", "lever", "checkbox", "valid"),
("NP-0550", "lever", "checkbox", "edge"),
("NP-0551", "workday", "text", "valid"),
("NP-0552", "workday", "text", "edge"),
("NP-0553", "workday", "email", "valid"),
("NP-0554", "workday", "email", "edge"),
("NP-0555", "workday", "phone", "valid"),
("NP-0556", "workday", "phone", "edge"),
("NP-0557", "workday", "select-dropdown", "valid"),
("NP-0558", "workday", "select-dropdown", "edge"),
("NP-0559", "workday", "multi-select", "valid"),
("NP-0560", "workday", "multi-select", "edge"),
("NP-0561", "workday", "date", "valid"),
("NP-0562", "workday", "date", "edge"),
("NP-0563", "workday", "file-upload", "valid"),
("NP-0564", "workday", "file-upload", "edge"),
("NP-0565", "workday", "textarea", "valid"),
("NP-0566", "workday", "textarea", "edge"),
("NP-0567", "workday", "radio", "valid"),
("NP-0568", "workday", "radio", "edge"),
("NP-0569", "workday", "checkbox", "valid"),
("NP-0570", "workday", "checkbox", "edge"),
("NP-0571", "naukri", "text", "valid"),
("NP-0572", "naukri", "text", "edge"),
("NP-0573", "naukri", "email", "valid"),
("NP-0574", "naukri", "email", "edge"),
("NP-0575", "naukri", "phone", "valid"),
("NP-0576", "naukri", "phone", "edge"),
("NP-0577", "naukri", "select-dropdown", "valid"),
("NP-0578", "naukri", "select-dropdown", "edge"),
("NP-0579", "naukri", "multi-select", "valid"),
("NP-0580", "naukri", "multi-select", "edge"),
("NP-0581", "naukri", "date", "valid"),
("NP-0582", "naukri", "date", "edge"),
("NP-0583", "naukri", "file-upload", "valid"),
("NP-0584", "naukri", "file-upload", "edge"),
("NP-0585", "naukri", "textarea", "valid"),
("NP-0586", "naukri", "textarea", "edge"),
("NP-0587", "naukri", "radio", "valid"),
("NP-0588", "naukri", "radio", "edge"),
("NP-0589", "naukri", "checkbox", "valid"),
("NP-0590", "naukri", "checkbox", "edge")
]

@pytest.mark.integration
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,ats,field,state", ROWS, ids=[r[0] for r in ROWS])
def test_e1_form_fill_matrix(case_id, ats, field, state, fixtures_root):
    html = (fixtures_root / "forms" / f"{ats}_apply.html").read_text(encoding="utf-8")
    assert f'data-ats="{ats}"' in html, case_id
    if state == "valid":
        intended = PROFILE[field]
        result = verify_field(
            field_id=f"{ats}.{field}",
            expected=intended,
            dom_value=intended,
            check_validity=True,
            aria={"aria-checked": True} if field in ("checkbox", "radio") else {},
            error_banners=[],
            model_value=intended,
        )
        assert result.ok is True, case_id
    else:
        intended = PROFILE[field]
        edge_val = EDGE[field]
        result = verify_field(
            field_id=f"{ats}.{field}",
            expected=intended,
            dom_value=edge_val,
            check_validity=False,
            error_banners=["invalid"] if field in ("email", "phone", "date") else [],
            model_value=edge_val,
        )
        # fail closed: must not report ok on garbage
        assert result.ok is False, case_id

