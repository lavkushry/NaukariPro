"""Notification queue with per-(user, job, channel) idempotency, delay, max 3 retries."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB = Path(__file__).resolve().parents[1] / "notifications.db"
MAX_RETRIES = 3
ALERT_DELAY_MINUTES = 15


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationQueue:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    job_key TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retries INTEGER NOT NULL DEFAULT 0,
                    send_after TEXT NOT NULL,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, job_key, channel)
                )
                """
            )

    def enqueue(
        self,
        *,
        user_id: str,
        job_key: str,
        channel: str,
        payload: str,
        delay_minutes: int = ALERT_DELAY_MINUTES,
    ) -> bool:
        """Returns False if idempotent duplicate exists."""
        send_after = (_now() + timedelta(minutes=delay_minutes)).isoformat()
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO notifications (
                        user_id, job_key, channel, payload, status, retries, send_after, created_at
                    ) VALUES (?,?,?,?, 'pending', 0, ?, ?)
                    """,
                    (user_id, job_key, channel, payload, send_after, _now().isoformat()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def due(self) -> List[Dict[str, Any]]:
        now = _now().isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notifications
                WHERE status='pending' AND send_after <= ? AND retries < ?
                ORDER BY send_after
                """,
                (now, MAX_RETRIES),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_sent(self, notif_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE notifications SET status='sent', sent_at=? WHERE id=?",
                (_now().isoformat(), notif_id),
            )

    def mark_failed(self, notif_id: int) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT retries FROM notifications WHERE id=?", (notif_id,)
            ).fetchone()
            retries = int(row["retries"] if row else 0) + 1
            status = "failed" if retries >= MAX_RETRIES else "pending"
            conn.execute(
                "UPDATE notifications SET retries=?, status=? WHERE id=?",
                (retries, status, notif_id),
            )

    def deliver_due(self, *, sink: Optional[Any] = None) -> int:
        """
        Deliver due notifications. Default sink prints (email/Telegram adapters plug in).
        Returns count sent.
        """
        sent = 0
        for n in self.due():
            try:
                if sink:
                    sink(n)
                else:
                    print(f"[notify:{n['channel']}] user={n['user_id']} job={n['job_key']} {n['payload'][:120]}")
                self.mark_sent(int(n["id"]))
                sent += 1
            except Exception:
                self.mark_failed(int(n["id"]))
        return sent
