#!/usr/bin/env python3
"""Generate parametrized scenario test modules for NP-0001…NP-1000 families."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SC = ROOT / "tests" / "scenarios"


def np(n: int) -> str:
    return f"NP-{n:04d}"


def write(rel: str, content: str) -> None:
    path = SC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip() + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


def gen_fixtures() -> None:
    boards = []
    companies = [
        "Flipkart", "Razorpay", "Freshworks", "Zoho", "PhonePe", "Swiggy",
        "Zomato", "CRED", "Groww", "Postman", "Chargebee", "BrowserStack",
        "Hasura", "Meesho", "ShareChat", "Dream11", "Dell", "Infosys",
        "TCS Digital", "Persistent", "Thoughtworks", "Atlassian India",
        "Adobe Noida", "Microsoft IDC", "Google Hyderabad", "Amazon India",
        "Uber India", "LinkedIn India", "Salesforce India", "NVIDIA Bengaluru",
        "Databricks India", "Oracle India", "SAP Labs", "Intel India",
        "Cisco Bengaluru", "Juspay", "Unacademy", "BYJU'S", "Ola", "Myntra",
    ]
    locs = ["Bengaluru", "Bangalore", "NCR", "Gurugram", "Noida", "Pune", "Hyderabad", "Remote (India)", "Chennai", "Mumbai"]
    boards_src = ["greenhouse", "ashby", "lever", "workday", "smartrecruiters", "workable", "recruitee", "naukri"]
    for i in range(200):
        b = boards_src[i % len(boards_src)]
        company = companies[i % len(companies)]
        loc = locs[i % len(locs)]
        boards.append(
            {
                "external_job_id": f"{b}-{i:04d}",
                "source_id": b,
                "ats_type": b,
                "company": company,
                "title": ["MLOps Engineer", "DevOps Engineer", "Platform Engineer", "SRE", "AI Infrastructure Engineer"][i % 5],
                "url": f"https://boards.{b}.example/jobs/{i}?utm_source=x&gclid=1",
                "location": loc,
                "salary": None if i % 7 == 0 else f"{12 + (i % 20)} LPA",
                "description_full": f"Build Kubernetes platforms. Notice period flexible. Role {i}.",
                "published_at": "2026-06-01T00:00:00+00:00" if i % 3 else "2025-01-01T00:00:00+00:00",
            }
        )
    (SC / "fixtures" / "boards" / "india_jobs_200.json").write_text(
        json.dumps(boards, indent=2), encoding="utf-8"
    )
    profile = {
        "name": "Lavkush Kumar",
        "email": "candidate@example.com",
        "phone": "+91-9876543210",
        "resume_text": (
            "DevOps Engineer with Kubernetes Docker Terraform AWS. "
            "Reduced deployment time from 45 minutes to 12 minutes. "
            "AWS Cloud Practitioner. Notice period 30 days. "
            "Current CTC 18 LPA. Expected CTC 28 LPA."
        ),
        "certificates": ["AWS Cloud Practitioner"],
        "numbers": ["45", "12", "30", "18", "28"],
        "project_bullets": [
            "Containerized 8 microservices on EKS with Helm.",
            "Instrumented Prometheus Grafana SLOs at 99.5 percent uptime.",
        ],
    }
    (SC / "fixtures" / "profile" / "golden_candidate.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )
    for ats in ("greenhouse", "ashby", "lever", "workday", "naukri"):
        html = f"""<!doctype html><html><body data-ats="{ats}">
<form id="application">
<input name="full_name" type="text" maxlength="80" />
<input name="email" type="email" />
<input name="phone" type="tel" />
<select name="country"><option>India</option><option>Other</option></select>
<select name="skills" multiple><option>Python</option><option>K8s</option></select>
<input name="start_date" type="date" />
<input name="resume" type="file" />
<textarea name="cover" maxlength="2000"></textarea>
<input type="radio" name="work_auth" value="yes" /><input type="radio" name="work_auth" value="no" />
<input type="checkbox" name="consent" />
</form></body></html>"""
        (SC / "fixtures" / "forms" / f"{ats}_apply.html").write_text(html, encoding="utf-8")
    golden = {
        "url_pairs": [
            ["https://Boards.Greenhouse.io/Acme/jobs/1/?utm_source=x&gclid=abc", "https://boards.greenhouse.io/Acme/jobs/1"],
            ["http://boards.ashbyhq.com/x/y/", "http://boards.ashbyhq.com/x/y"],
        ],
        "decay_vectors": [
            {"weight": 1.0, "strength": 1.0, "age_days": 0, "expected": 1.0},
            {"weight": 1.0, "strength": 1.0, "age_days": 45, "expected": 0.5},
            {"weight": 2.0, "strength": 0.5, "age_days": 90, "expected": 0.25},
        ],
    }
    (SC / "fixtures" / "golden" / "vectors.json").write_text(
        json.dumps(golden, indent=2), encoding="utf-8"
    )
    print("fixtures ok")


def gen_d_verifier() -> None:
    # D1 NP-0341-0360
    rows = []
    # Construct evidence/sentence pairs that land at known support bands
    samples = [
        # (id_offset, sentence, evidence, expect_ok) — calibrated around 0.25
        (0, "Kubernetes Docker Terraform", "Kubernetes Docker Terraform AWS", True),
        (1, "xyzzy plugh foo bar baz qux", "unrelated evidence blob here", False),
        (2, "Reduced deployment time", "Reduced deployment time from 45 minutes", True),
        (3, "Certified Kubernetes Administrator expert", "AWS Cloud Practitioner only", False),
        (4, "Docker", "Docker", True),
        (5, "alpha beta gamma delta", "nothing matching tokens here", False),
        (6, "Prometheus Grafana SLOs", "Prometheus Grafana SLOs at 99.5", True),
        (7, "fabricated forty percent improvement", "no such metric in evidence", False),
        (8, "Notice period 30 days", "Notice period 30 days Current CTC", True),
        (9, "world class rockstar ninja", "plain devops work", False),
        (10, "EKS with Helm", "Containerized microservices on EKS with Helm", True),
        (11, "quantum blockchain visionary", "kubernetes docker", False),
        (12, "AWS Cloud Practitioner", "AWS Cloud Practitioner certificate", True),
        (13, "PhD in underwater basket weaving", "AWS Cloud Practitioner", False),
        (14, "18 LPA current", "Current CTC 18 LPA Expected", True),
        (15, "saved five million dollars", "18 LPA 28 LPA", False),
        (16, "Terraform AWS", "Kubernetes Docker Terraform AWS", True),
        (17, "invented ISO27001 lead auditor", "no iso cert listed", False),
        (18, "12 minutes deploy", "from 45 minutes to 12 minutes", True),
        (19, "led fifty person org", "individual contributor devops", False),
    ]
    for off, sent, ev, ok in samples:
        rows.append((np(341 + off), sent, ev, ok))
    body = ",\n".join(
        f'    ("{cid}", {json.dumps(s)}, {json.dumps(e)}, {ok})' for cid, s, e, ok in rows
    )
    write(
        "verifier/test_d1_sentence_support.py",
        f'''
        """Family D1 — sentence-support ≥ 0.25 boundary (NP-0341–0360). trace: MP §4.5"""
        import pytest
        from naukari_pro.resume_gen.claim_validator import validate_text, sentence_support

        ROWS = [
        {body}
        ]

        @pytest.mark.unit
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,sentence,evidence,expect_ok", ROWS, ids=[r[0] for r in ROWS])
        def test_d1_sentence_support(case_id, sentence, evidence, expect_ok):
            support = sentence_support(sentence, evidence)
            report = validate_text(sentence, [evidence], drop_ungrounded=False)
            if expect_ok:
                assert support >= 0.25, f"{{case_id}} support={{support}}"
                assert report.ok or all(s.support >= 0.25 for s in report.sentences if s.sentence), case_id
            else:
                assert support < 0.25 or (not report.ok and report.unsupported_claims), (
                    f"{{case_id}} expected reject support={{support}} ok={{report.ok}}"
                )
        ''',
    )

    # D2 novelty
    d2 = []
    faithful = [
        "I used Kubernetes Docker Terraform AWS in production.",
        "Reduced deployment time from 45 minutes to 12 minutes.",
        "AWS Cloud Practitioner. Notice period 30 days.",
        "Current CTC 18 LPA. Expected CTC 28 LPA.",
        "Containerized microservices on EKS with Helm.",
    ]
    polished = [
        "I orchestrated a world-class synergy of container orchestration paradigms across polyglot estates.",
        "Leveraging cutting-edge methodologies I revolutionized delivery velocity exponentially.",
        "As a passionate results-driven professional I spearheaded transformational initiatives.",
        "My holistic approach unlocked unprecedented stakeholder value across the tapestry.",
        "I fostered a culture of excellence driving impactful paradigm shifts daily.",
    ]
    evidence = (
        "DevOps Engineer with Kubernetes Docker Terraform AWS. "
        "Reduced deployment time from 45 minutes to 12 minutes. "
        "AWS Cloud Practitioner. Notice period 30 days. "
        "Current CTC 18 LPA. Expected CTC 28 LPA. "
        "Containerized 8 microservices on EKS with Helm."
    )
    for i in range(20):
        cid = np(361 + i)
        if i < 8:
            text, expect = faithful[i % len(faithful)], True
        elif i < 14:
            text, expect = polished[i % len(polished)], False
        else:
            # boundary band — heavily novel paraphrase
            text, expect = polished[i % len(polished)] + " synergistic excellence", False
        d2.append((cid, text, expect))
    body = ",\n".join(f'    ("{a}", {json.dumps(b)}, {c})' for a, b, c in d2)
    write(
        "verifier/test_d2_novelty_cap.py",
        f'''
        """Family D2 — novelty-ratio ≤ 0.34 cap (NP-0361–0380). trace: MP §4.5"""
        import pytest
        from naukari_pro.resume_gen.claim_validator import validate_text, novelty_ratio

        EVIDENCE = {json.dumps(evidence)}
        ROWS = [
        {body}
        ]

        @pytest.mark.unit
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,text,expect_ok", ROWS, ids=[r[0] for r in ROWS])
        def test_d2_novelty_cap(case_id, text, expect_ok):
            report = validate_text(text, [EVIDENCE])
            ratio = report.novelty_ratio
            if expect_ok:
                assert report.ok and ratio <= 0.34, f"{{case_id}} ratio={{ratio}} claims={{report.unsupported_claims}}"
            else:
                assert (not report.ok) or ratio > 0.34, f"{{case_id}} should reject ratio={{ratio}}"
        ''',
    )

    # D3 puffery 20
    puff_words = [
        "world-class", "rockstar ninja", "10x engineer", "best-in-class", "cutting-edge",
        "proven track record", "highly skilled", "passionate", "synergy", "robust solution",
        "spearheaded transformational", "effective leader", "crucial expert", "fostered excellence",
        "leveraged synergies", "game-changer", "visionary genius", "elite performer",
        "unparalleled mastery", "legendary coder",
    ]
    body = ",\n".join(
        f'    ("{np(381+i)}", {json.dumps(w)})' for i, w in enumerate(puff_words)
    )
    write(
        "verifier/test_d3_puffery.py",
        f'''
        """Family D3 — PUFFERY regex (NP-0381–0400). trace: MP §4.5"""
        import pytest
        from naukari_pro.resume_gen.claim_validator import PUFFERY, validate_text

        ROWS = [
        {body}
        ]

        @pytest.mark.redteam
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,phrase", ROWS, ids=[r[0] for r in ROWS])
        def test_d3_puffery(case_id, phrase):
            sentence = f"I am a {{phrase}} DevOps engineer delivering results."
            # Either regex hits OR validate_text rejects unsupported puffery
            hit = bool(PUFFERY.search(sentence)) or bool(PUFFERY.search(phrase))
            report = validate_text(sentence, ["DevOps engineer kubernetes"])
            assert hit or (not report.ok and report.unsupported_claims), case_id
        ''',
    )

    # D4 verbatim numbers 25
    d4 = []
    for i in range(25):
        cid = np(401 + i)
        if i < 12:
            d4.append((cid, f"Reduced time to {12 + i % 5} minutes.", True, f"{12 + i % 5}"))
        else:
            d4.append((cid, f"Improved metrics by {40 + i}% year over year.", False, None))
    body = ",\n".join(
        f'    ("{a}", {json.dumps(b)}, {c}, {json.dumps(d)})' for a, b, c, d in d4
    )
    write(
        "verifier/test_d4_verbatim_numbers.py",
        f'''
        """Family D4 — verbatim number/cert match (NP-0401–0425). trace: MP §4.5"""
        import pytest
        from naukari_pro.resume_gen.claim_validator import validate_text

        EVIDENCE = [
            "Reduced deployment time from 45 minutes to 12 minutes.",
            "13 minutes", "14 minutes", "15 minutes", "16 minutes",
            "AWS Cloud Practitioner", "18 LPA", "28 LPA", "30 days",
        ]
        ROWS = [
        {body}
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
        ''',
    )

    # D5 answer contract 15
    write(
        "verifier/test_d5_answer_contract.py",
        '''
        """Family D5 — answer contract shape (NP-0426–0440). trace: MP §4.5"""
        import pytest
        from naukari_pro.governed_apply.screening_answers import answer_screening_question

        QUESTIONS = [
            "Notice period?", "Current CTC?", "Expected CTC?", "Are you open to relocate?",
            "Years of Kubernetes?", "Visa status?", "Earliest start date?", "Willing to work nights?",
            "Python experience?", "AWS experience?", "Onsite preference?", "Bond obligation?",
            "Reference available?", "Hybrid ok?", "Why this role?",
        ]
        ROWS = [(f"NP-{426+i:04d}", QUESTIONS[i]) for i in range(15)]

        @pytest.mark.contract
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,question", ROWS, ids=[r[0] for r in ROWS])
        def test_d5_answer_contract(case_id, question, profile_evidence):
            ans = answer_screening_question(profile=profile_evidence, question=question)
            assert isinstance(ans, dict), case_id
            assert "reason" in ans and "answer" in ans, case_id
            assert ans["reason"] in ("ok", "ASK_USER"), case_id
        ''',
    )

    # D6 writing lint — 30 of ~60 phrases
    phrases = [
        "as an ai", "in today's fast-paced", "delve into", "tapestry", "multifaceted",
        "leverage synergies", "seamless integration", "cutting-edge", "game-changer",
        "passionate about", "thrilled to", "excited to apply", "perfect fit",
        "hit the ground running", "synergistic", "holistic approach", "paradigm shift",
        "keen eye for detail", "think outside the box", "move the needle",
        "circle back", "low-hanging fruit", "at the end of the day", "going forward",
        "first and foremost", "needless to say", "very unique", "results-driven professional",
        "self-starter with", "team player who",
    ]
    body = ",\n".join(f'    ("{np(441+i)}", {json.dumps(p)})' for i, p in enumerate(phrases))
    write(
        "verifier/test_d6_writing_lint.py",
        f'''
        """Family D6 — writing lint banned phrases (NP-0441–0470). trace: MP §4.5"""
        import pytest
        from naukari_pro.resume_gen.writing_lint import lint_text, BANNED_PHRASES

        ROWS = [
        {body}
        ]

        @pytest.mark.unit
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,phrase", ROWS, ids=[r[0] for r in ROWS])
        def test_d6_writing_lint(case_id, phrase):
            assert any(phrase in b for b in BANNED_PHRASES) or phrase in BANNED_PHRASES, case_id
            verdict = lint_text(f"Dear team, {{phrase}} I deliver value.")
            assert verdict.verdict in ("REWRITE", "DO NOT SEND", "PASS"), case_id
            assert verdict.verdict != "PASS" or phrase not in f"Dear team, {{phrase}} I deliver value.".lower()
            # Prefer reject/rewrite for banned content
            assert verdict.verdict in ("REWRITE", "DO NOT SEND"), f"{{case_id}} verdict={{verdict.verdict}}"
        ''',
    )

    # D7 determinism 20
    write(
        "verifier/test_d7_tailoring_determinism.py",
        '''
        """Family D7 — tailoring determinism (NP-0471–0490). trace: MP §4.4"""
        import pytest
        from naukari_pro.resume_gen.claim_validator import validate_text

        ROWS = [(f"NP-{471+i:04d}", i) for i in range(20)]
        TEXT = "Reduced deployment time from 45 minutes to 12 minutes using Kubernetes."
        EV = ["Reduced deployment time from 45 minutes to 12 minutes", "Kubernetes"]

        @pytest.mark.unit
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
        def test_d7_tailoring_determinism(case_id, idx):
            a = validate_text(TEXT, EV).to_dict()
            b = validate_text(TEXT, EV).to_dict()
            assert a == b, case_id
            assert a["ok"] is True, case_id
        ''',
    )


def gen_f_captcha() -> None:
    types = [
        "recaptcha_v2", "recaptcha_v3", "hcaptcha", "turnstile",
        "funcaptcha", "geetest", "image_captcha", "text_captcha",
    ]
    html_map = {
        "recaptcha_v2": '<div class="g-recaptcha" data-sitekey="x"></div>',
        "recaptcha_v3": '<script src="recaptcha/enterprise.js"></script><script>grecaptcha.execute</script>',
        "hcaptcha": '<div class="h-captcha" data-sitekey="x"></div>',
        "turnstile": '<div class="cf-turnstile"></div>',
        "funcaptcha": '<div class="arkose" data-callback="x"></div>',
        "geetest": '<div class="geetest" id="gt_captcha"></div>',
        "image_captcha": '<img class="captcha-image"/><input id="captcha"/>',
        "text_captcha": "<p>Type the characters shown below</p>",
    }
    rows = []
    i = 0
    for t in types:
        for variant in ("present", "absent_noise", "mixed"):
            cid = np(681 + i)
            if variant == "present":
                html, expect = html_map[t], t
            elif variant == "absent_noise":
                html, expect = "<html><body>Apply now clean form</body></html>", None
            else:
                html, expect = html_map[t] + "<!-- captcha -->", t
            rows.append((cid, t, html, expect if variant != "absent_noise" else None))
            i += 1
    assert len(rows) == 24
    body = ",\n".join(
        f'    ("{a}", {json.dumps(b)}, {json.dumps(c)}, {json.dumps(d)})' for a, b, c, d in rows
    )
    write(
        "captcha/test_f1_detector.py",
        f'''
        """Family F1 — captcha detector 8×3 (NP-0681–0704). trace: MP §4.9"""
        import pytest
        from naukari_pro.governed_apply.attention import detect_blocker, BlockerClass
        from naukari_pro.governed_apply.captcha_safety import detect_captcha_type

        ROWS = [
        {body}
        ]

        @pytest.mark.unit
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,ctype,html,expect", ROWS, ids=[r[0] for r in ROWS])
        def test_f1_detector(case_id, ctype, html, expect):
            detected = detect_captcha_type(html)
            blocker = detect_blocker(html)
            if expect is None:
                assert detected is None, case_id
                assert blocker != BlockerClass.CAPTCHA, case_id
            else:
                assert detected == expect or detected == "unknown_captcha", case_id
                assert blocker == BlockerClass.CAPTCHA, case_id
        ''',
    )

    f2 = [
        (np(705), "human", None, ["*"], 0.0, 5.0, "boards.greenhouse.io", False),
        (np(706), "vendor", None, ["*"], 0.0, 5.0, "boards.greenhouse.io", False),
        (np(707), "vendor", "k", [], 0.0, 5.0, "boards.greenhouse.io", False),
        (np(708), "vendor", "k", ["*.ashbyhq.com"], 0.0, 5.0, "boards.greenhouse.io", False),
        (np(709), "vendor", "k", ["*"], 5.0, 5.0, "boards.ashbyhq.com", False),
        (np(710), "vendor", "k", ["*"], 4.9, 5.0, "boards.ashbyhq.com", True),
        (np(711), "vendor", "k", ["boards.greenhouse.io"], 0.0, 5.0, "boards.greenhouse.io", True),
        (np(712), "human", "k", ["*"], 0.0, 5.0, "boards.ashbyhq.com", False),
        (np(713), "vendor", "k", ["*"], 5.1, 5.0, "boards.ashbyhq.com", False),
        (np(714), "vendor", "", ["*"], 0.0, 5.0, "boards.ashbyhq.com", False),
        (np(715), "vendor", "k", ["boards.lever.co"], 0.0, 5.0, "boards.ashbyhq.com", False),
        (np(716), "vendor", "k", ["*"], 0.0, 5.0, "boards.lever.co", True),
        (np(717), "human", None, [], 0.0, 5.0, "boards.greenhouse.io", False),
        (np(718), "vendor", "k", ["*"], 4.99, 5.0, "jobs.workday.com", True),
        (np(719), "vendor", "k", ["jobs.workday.com"], 0.0, 1.0, "jobs.workday.com", True),
        (np(720), "vendor", "k", ["*"], 1.0, 1.0, "jobs.workday.com", False),
        (np(721), "vendor", "k", ["*"], 0.0, 5.0, "evil.example", True),  # * allow
        (np(722), "vendor", "k", ["evil.example"], 0.0, 5.0, "evil.example", True),
        (np(723), "vendor", "k", ["good.example"], 0.0, 5.0, "evil.example", False),
        (np(724), "human", "k", ["*"], 0.0, 5.0, "evil.example", False),
    ]
    body = ",\n".join(
        f'    ("{a}", "{b}", {json.dumps(c)}, {d}, {e}, {f}, "{g}", {h})'
        for a, b, c, d, e, f, g, h in f2
    )
    write(
        "captcha/test_f2_mode_matrix.py",
        f'''
        """Family F2 — captcha mode matrix (NP-0705–0724). trace: MP §4.9"""
        import pytest
        from naukari_pro.governed_apply.captcha_safety import CaptchaSafetyManager, Resolution

        ROWS = [
        {body}
        ]

        @pytest.mark.redteam
        @pytest.mark.scenario
        @pytest.mark.parametrize(
            "case_id,mode,key,allowlist,spend,cap,domain,vendor_called",
            ROWS,
            ids=[r[0] for r in ROWS],
        )
        def test_f2_mode_matrix(case_id, mode, key, allowlist, spend, cap, domain, vendor_called):
            calls = {{"n": 0}}

            def vendor(**kwargs):
                calls["n"] += 1
                return True

            mgr = CaptchaSafetyManager(
                mode=mode,
                api_key=key,
                domains=allowlist,
                spend_24h=spend,
                cap=cap,
                vendor_callable=vendor,
            )
            if mode == "human":
                assert mgr._vendor is None, case_id
            result = mgr.handle(captcha_type="hcaptcha", page_url=f"https://{{domain}}/x")
            asserted_vendor = result.resolved_by == "vendor"
            assert asserted_vendor == vendor_called, (
                f"{{case_id}} expected vendor_called={{vendor_called}} got resolved_by={{result.resolved_by}} detail={{result.detail}}"
            )
            assert result.resolution != Resolution.APPLIED_INVALID, case_id
            if not vendor_called:
                assert calls["n"] == 0 or result.vendor_attempted is False or mode == "human", case_id
        ''',
    )

    write(
        "captcha/test_f3_ledger_breaker.py",
        '''
        """Family F3 — ledger + circuit breaker + exit 3 (NP-0725–0740). trace: MP §4.9"""
        import pytest
        from naukari_pro.governed_apply.captcha_safety import (
            CaptchaSafetyManager,
            EXIT_CAPTCHA_BLOCKED,
            Resolution,
        )

        ROWS = [(f"NP-{725+i:04d}", i) for i in range(16)]

        @pytest.mark.integration
        @pytest.mark.scenario
        @pytest.mark.parametrize("case_id,idx", ROWS, ids=[r[0] for r in ROWS])
        def test_f3_ledger_breaker(case_id, idx, tmp_sqlite_wal):
            board = f"board-{idx % 3}"
            mgr = CaptchaSafetyManager(mode="human", db_path=tmp_sqlite_wal, board=board)
            # seed unresolved
            for _ in range(min(idx, 6)):
                CaptchaSafetyManager(mode="human", db_path=tmp_sqlite_wal, board=board).handle(
                    captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x"
                )
            result = mgr.handle(captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x")
            assert result.exit_code == EXIT_CAPTCHA_BLOCKED, case_id
            assert result.resolution in (Resolution.NEEDS_HUMAN, Resolution.CIRCUIT_OPEN, Resolution.VENDOR_DENIED), case_id
            if idx >= 5:
                # after ≥5 unresolved, circuit should open on subsequent handle
                tripped = CaptchaSafetyManager(mode="vendor", api_key="k", domains=["*"], db_path=tmp_sqlite_wal, board=board, vendor_callable=lambda **k: True).handle(
                    captcha_type="hcaptcha", page_url="https://boards.greenhouse.io/x"
                )
                assert tripped.resolution == Resolution.CIRCUIT_OPEN or tripped.exit_code == EXIT_CAPTCHA_BLOCKED, case_id
        ''',
    )


def main() -> None:
    gen_fixtures()
    gen_d_verifier()
    gen_f_captcha()
    # remaining families via second pass
    from scripts import _gen_scenario_rest as rest  # noqa — inline below


if __name__ == "__main__":
    gen_fixtures()
    gen_d_verifier()
    gen_f_captcha()
    print("partial generation done — run rest")
