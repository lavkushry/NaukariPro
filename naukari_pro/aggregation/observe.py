"""7-day observation digest scaffold for multi-board ingest before permanent submit unlock."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.models import utc_now_iso
from naukari_pro.aggregation.storage import AggregationStore

DEFAULT_DIGEST_DIR = Path(__file__).resolve().parents[1] / "runtime" / "observe"


def observation_window_days(days: int = 7) -> List[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days)]


def build_7d_digest(store: Optional[AggregationStore] = None) -> Dict[str, Any]:
    store = store or AggregationStore()
    days = observation_window_days(7)
    with store._connect() as conn:
        rows = conn.execute(
            """
            SELECT board_day, COUNT(DISTINCT source_id) boards,
                   SUM(fetch_ok) ok, SUM(fetch_err) err,
                   SUM(jobs_seen) seen, SUM(jobs_new) newj
            FROM board_health
            WHERE board_day IN ({placeholders})
            GROUP BY board_day
            ORDER BY board_day DESC
            """.format(placeholders=",".join("?" * len(days))),
            days,
        ).fetchall()
        cycles = conn.execute(
            """
            SELECT cycle_id, event, detail, created_at FROM cycle_log
            ORDER BY id DESC LIMIT 50
            """
        ).fetchall()
    by_day = [
        {
            "board_day": r["board_day"],
            "boards": r["boards"],
            "fetch_ok": r["ok"],
            "fetch_err": r["err"],
            "jobs_seen": r["seen"],
            "jobs_new": r["newj"],
        }
        for r in rows
    ]
    return {
        "generated_at": utc_now_iso(),
        "window_days": days,
        "by_day": by_day,
        "healthy_boards": store.healthy_boards(),
        "verified_boards_total": store.verified_boards_total(),
        "recent_cycles": [
            {
                "cycle_id": c["cycle_id"],
                "event": c["event"],
                "detail": c["detail"],
                "created_at": c["created_at"],
            }
            for c in cycles
        ],
        "submit_unlock_permanent": False,
        "note": "Observe multi-board ingest for 7 days before treating submit unlock as permanent.",
    }


def write_7d_digest(
    store: Optional[AggregationStore] = None,
    *,
    dest_dir: Optional[Path] = None,
) -> Path:
    digest = build_7d_digest(store)
    dest = Path(dest_dir) if dest_dir else DEFAULT_DIGEST_DIR
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"observe_7d_{utc_now_iso()[:10]}.json"
    path.write_text(json.dumps(digest, indent=2), encoding="utf-8")
    return path
