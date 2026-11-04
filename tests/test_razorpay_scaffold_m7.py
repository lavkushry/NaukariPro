"""M7: Razorpay scaffold + single-use coupons (offline)."""

from naukari_pro.billing.razorpay_scaffold import RazorpayScaffold


def test_coupon_single_use_and_meter():
    bill = RazorpayScaffold()
    bill.register_coupon("LAUNCH100")
    payload = bill.create_subscription_payload(customer_email="a@b.com", coupon="LAUNCH100")
    assert payload["amount"] == 0  # 100% off before redeem marks used
    c = bill.redeem_coupon("LAUNCH100")
    assert c is not None
    assert bill.redeem_coupon("LAUNCH100") is None
    assert bill.meter("tailor", 2) == 2
    assert bill.meter("autofill") == 1


def test_webhook_signature_requires_secret(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "sekrit")
    bill = RazorpayScaffold()
    ok = bill.verify_webhook_signature(b'{"a":1}', "deadbeef")
    assert ok is False
