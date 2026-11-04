"""Apply v2 exit-code contract (MP §4.6)."""

EXIT_OK = 0
EXIT_SOFT_FAIL = 1
EXIT_HARD_SKIP = 2
EXIT_CAPTCHA_BLOCKED = 3
EXIT_APPROVAL_DENIED = 4

EXIT_LABELS = {
    EXIT_OK: "ok",
    EXIT_SOFT_FAIL: "soft_fail",
    EXIT_HARD_SKIP: "hard_skip",
    EXIT_CAPTCHA_BLOCKED: "captcha_blocked",
    EXIT_APPROVAL_DENIED: "approval_denied",
}
