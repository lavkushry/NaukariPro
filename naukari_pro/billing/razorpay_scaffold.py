"""Razorpay billing scaffold (jobRadar ₹49/mo template) — no live charges in tests."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

DEFAULT_PLAN_INR = 49
DEFAULT_CURRENCY = "INR"


@dataclass
class Coupon:
    code: str
    single_use: bool = True
    used: bool = False
    percent_off: int = 100


class RazorpayScaffold:
    """
    Config-only scaffold. Real Razorpay SDK calls stay behind env flags.
    Meter autofill/tailor counts for future usage billing (autoapplycv pattern).
    """

    def __init__(self) -> None:
        self.key_id = os.environ.get("RAZORPAY_KEY_ID", "")
        self.key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
        self.plan_inr = int(os.environ.get("RAZORPAY_PLAN_INR", DEFAULT_PLAN_INR))
        self.enabled = bool(self.key_id and self.key_secret)
        self.coupons: Dict[str, Coupon] = {}
        self.meters: Dict[str, int] = {"autofill": 0, "tailor": 0}

    def register_coupon(self, code: str, *, percent_off: int = 100) -> Coupon:
        c = Coupon(code=code.upper().strip(), percent_off=percent_off)
        self.coupons[c.code] = c
        return c

    def redeem_coupon(self, code: str) -> Optional[Coupon]:
        c = self.coupons.get((code or "").upper().strip())
        if not c or (c.single_use and c.used):
            return None
        c.used = True
        return c

    def meter(self, event: str, n: int = 1) -> int:
        self.meters[event] = int(self.meters.get(event) or 0) + n
        return self.meters[event]

    def create_subscription_payload(self, *, customer_email: str, coupon: str = "") -> Dict[str, Any]:
        amount = self.plan_inr * 100  # paise
        if coupon:
            c = self.coupons.get(coupon.upper())
            if c and not c.used:
                amount = int(amount * (100 - c.percent_off) / 100)
        return {
            "amount": amount,
            "currency": DEFAULT_CURRENCY,
            "plan_label": f"NaukariPro ₹{self.plan_inr}/mo",
            "customer_email": customer_email,
            "enabled": self.enabled,
            "note": "Scaffold only — set RAZORPAY_KEY_* to enable live checkout",
        }

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        if not self.key_secret:
            return False
        digest = hmac.new(self.key_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature or "")
