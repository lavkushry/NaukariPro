"""Family F1 — captcha detector 8×3 (NP-0681–0704). trace: MP §4.9"""
import pytest
from naukari_pro.governed_apply.attention import detect_blocker, BlockerClass
from naukari_pro.governed_apply.captcha_safety import detect_captcha_type

ROWS = [
    ("NP-0681", "recaptcha_v2", "<div class=\"g-recaptcha\" data-sitekey=\"x\"></div>", "recaptcha_v2"),
("NP-0682", "recaptcha_v2", "<html><body>Apply now clean form</body></html>", None),
("NP-0683", "recaptcha_v2", "<div class=\"g-recaptcha\" data-sitekey=\"x\"></div><!-- captcha -->", "recaptcha_v2"),
("NP-0684", "recaptcha_v3", "<script src=\"recaptcha/enterprise.js\"></script><script>grecaptcha.execute</script>", "recaptcha_v3"),
("NP-0685", "recaptcha_v3", "<html><body>Apply now clean form</body></html>", None),
("NP-0686", "recaptcha_v3", "<script src=\"recaptcha/enterprise.js\"></script><script>grecaptcha.execute</script><!-- captcha -->", "recaptcha_v3"),
("NP-0687", "hcaptcha", "<div class=\"h-captcha\" data-sitekey=\"x\"></div>", "hcaptcha"),
("NP-0688", "hcaptcha", "<html><body>Apply now clean form</body></html>", None),
("NP-0689", "hcaptcha", "<div class=\"h-captcha\" data-sitekey=\"x\"></div><!-- captcha -->", "hcaptcha"),
("NP-0690", "turnstile", "<div class=\"cf-turnstile\"></div>", "turnstile"),
("NP-0691", "turnstile", "<html><body>Apply now clean form</body></html>", None),
("NP-0692", "turnstile", "<div class=\"cf-turnstile\"></div><!-- captcha -->", "turnstile"),
("NP-0693", "funcaptcha", "<div class=\"arkose\" data-callback=\"x\"></div>", "funcaptcha"),
("NP-0694", "funcaptcha", "<html><body>Apply now clean form</body></html>", None),
("NP-0695", "funcaptcha", "<div class=\"arkose\" data-callback=\"x\"></div><!-- captcha -->", "funcaptcha"),
("NP-0696", "geetest", "<div class=\"geetest\" id=\"gt_captcha\"></div>", "geetest"),
("NP-0697", "geetest", "<html><body>Apply now clean form</body></html>", None),
("NP-0698", "geetest", "<div class=\"geetest\" id=\"gt_captcha\"></div><!-- captcha -->", "geetest"),
("NP-0699", "image_captcha", "<img class=\"captcha-image\"/><input id=\"captcha\"/>", "image_captcha"),
("NP-0700", "image_captcha", "<html><body>Apply now clean form</body></html>", None),
("NP-0701", "image_captcha", "<img class=\"captcha-image\"/><input id=\"captcha\"/><!-- captcha -->", "image_captcha"),
("NP-0702", "text_captcha", "<p>Type the characters shown below</p>", "text_captcha"),
("NP-0703", "text_captcha", "<html><body>Apply now clean form</body></html>", None),
("NP-0704", "text_captcha", "<p>Type the characters shown below</p><!-- captcha -->", "text_captcha")
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

