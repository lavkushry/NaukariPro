"""Per-board captcha circuit breaker."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

CIRCUIT_UNRESOLVED_THRESHOLD = 5
CIRCUIT_WINDOW_HOURS = 24


def circuit_open(
    db_path: Optional[Path],
    board: str,
    *,
    threshold: int = CIRCUIT_UNRESOLVED_THRESHOLD,
    window_hours: int = CIRCUIT_WINDOW_HOURS,
) -> bool:
    if not db_path or not Path(db_path).exists():
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        # Prefer captcha_events; fall back to captcha_ledger
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM captcha_events
                WHERE board = ?
                  AND ts >= ?
                  AND resolution IN ('needs_human','circuit_open','vendor_denied')
                """,
                (board, cutoff),
            ).fetchone()
            if row and int(row[0]) >= threshold:
                return True
        except sqlite3.OperationalError:
            pass
        row = conn.execute(
            """
            SELECT COUNT(*) FROM captcha_ledger
            WHERE board = ? AND unresolved = 1 AND created_at >= ?
            """,
            (board, cutoff),
        ).fetchone()
    return int(row[0] if row else 0) >= threshold
