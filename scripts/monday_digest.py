"""
scripts/monday_digest.py
Facade for naukari_pro.modules.learning.monday_digest.
Preserves backward compatibility for CLI commands and systemd services.
"""

from naukari_pro.modules.learning.monday_digest import (
    generate_monday_digest,
    send_monday_digest_email,
    main,
)

__all__ = [
    "generate_monday_digest",
    "send_monday_digest_email",
    "main",
]

if __name__ == "__main__":
    main()
