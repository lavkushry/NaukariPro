"""Weekly digest builder (email/Telegram payload)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from naukari_pro.tracking.store import TrackingStore


def build_weekly_digest(store: Optional[TrackingStore] = None) -> Dict[str, Any]:
    store = store or TrackingStore()
    funnel = store.funnel_counts()
    hist = store.rejection_histogram()
    by_ats = store.rejection_rate_by_ats()
    feed = store.feed(limit=5)
    lines = [
        f"NaukariPro Weekly Digest — {datetime.now(timezone.utc).date().isoformat()}",
        "",
        "Funnel:",
        *[f"  - {k}: {v}" for k, v in funnel.items()],
        "",
        "Rejection timing:",
        *[f"  - {k}: {v}" for k, v in hist.items()],
        "",
        "Rejection rate by ATS:",
        *([f"  - {k}: {v:.0%}" for k, v in by_ats.items()] or ["  - (none)"]),
        "",
        "Top scored saved/applied:",
        *([
            f"  - [{r.get('fit_score')}] {r.get('company')} — {r.get('title')} ({r.get('status')})"
            for r in feed
        ] or ["  - (empty)"]),
    ]
    text = "\n".join(lines)
    return {"subject": "NaukariPro Weekly Digest", "body": text, "funnel": funnel}
