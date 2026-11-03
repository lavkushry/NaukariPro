"""
tests/test_mail_reader.py

Unit tests for IMAPMailReader (H5 ATS verification link and code extraction).
Validates regex extraction, credential safety, and email parsing without network calls.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from naukari_pro.modules.mail_reader import (
    IMAPMailReader,
    VERIFY_LINK_RE,
    GENERIC_HTTPS_RE,
    OTP_RE,
    mail_test,
)


def test_verify_link_regex():
    """Verify link regex matches various ATS verification formats."""
    samples = [
        "Please confirm your email by clicking https://myworkdayjobs.com/verify?token=abc123xyz to activate.",
        "Click here: https://boards.greenhouse.io/confirm_email/987654?auth=true",
        "Activation link: https://jobs.lever.co/candidate/activation/abc-def-123",
        "Your code is ready. Complete signup at https://jobs.ashbyhq.com/token/xyz-token-123.",
    ]
    for sample in samples:
        m = VERIFY_LINK_RE.search(sample)
        assert m is not None, f"Failed to match verify link in: {sample}"
        assert m.group(0).startswith("http")


def test_otp_code_regex():
    """Verify OTP regex matches 4-8 digit codes."""
    samples = [
        ("Your verification code is 482910.", "482910"),
        ("Enter OTP: 9482 to continue your application.", "9482"),
        ("Your passcode is 12345678, valid for 10 minutes.", "12345678"),
    ]
    for text, expected in samples:
        m = OTP_RE.search(text)
        assert m is not None
        assert m.group(1) == expected


def test_credential_safety_when_unset():
    """Verify IMAPMailReader fails gracefully without credentials and never leaks secrets."""
    with patch.dict(os.environ, {}, clear=True):
        reader = IMAPMailReader(user="", password="")
        result = reader.test_connection()
        assert result["ok"] is False
        assert "missing" in result["error"].lower() or "unset" in result["user"].lower()


def test_fetch_verification_link_from_mock_message():
    """Verify fetch_verification_link parses email message body cleanly."""
    reader = IMAPMailReader(user="test@example.com", password="dummy_password")

    mock_msg = {
        "subject": "Please verify your email address",
        "from": "no-reply@myworkday.com",
        "date": "Tue, 03 Nov 2026 12:00:00 +0000",
        "body": "Thank you for applying. Click https://wd3.myworkdayjobs.com/verify?token=tok9988 to verify your account.",
    }

    with patch.object(reader, "fetch_recent_messages", return_value=[mock_msg]):
        link = reader.fetch_verification_link(sender_filter="myworkday.com")
        assert link == "https://wd3.myworkdayjobs.com/verify?token=tok9988"


def test_fetch_verification_code_from_mock_message():
    """Verify fetch_verification_code extracts OTP code near keywords."""
    reader = IMAPMailReader(user="test@example.com", password="dummy_password")

    mock_msg = {
        "subject": "Your Workday verification code",
        "from": "no-reply@myworkday.com",
        "date": "Tue, 03 Nov 2026 12:00:00 +0000",
        "body": "Your one-time security code is: 583921. It expires in 15 minutes.",
    }

    with patch.object(reader, "fetch_recent_messages", return_value=[mock_msg]):
        code = reader.fetch_verification_code(sender_filter="myworkday.com")
        assert code == "583921"
