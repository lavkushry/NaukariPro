"""
LinkedIn / Naukri browser connector posture.

Default: LINKEDIN_LITE — discovery leads only (title/company/location/url),
then probe-before-trust into ATS registry. Applications stay on real boards.

LINKEDIN_FULL requires an explicit config_audit opt-in row.
Challenge / bot-wall → 24h self-disable + screenshot event (never loop-retry).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.models import utc_now_iso
from naukari_pro.aggregation.storage import AggregationStore

MODE_LITE = "LINKEDIN_LITE"
MODE_FULL = "LINKEDIN_FULL"
CONFIG_KEY_LINKEDIN_MODE = "linkedin_browser_mode"
CONFIG_KEY_DISABLED_UNTIL = "browser_connector_disabled_until"
CHALLENGE_DISABLE_HOURS = 24
SELECTOR_PACK_VERSION = "naukri-cards-v1"
PARSE_MINIMUM_CARDS = 5


@dataclass
class DiscoveryLead:
    title: str
    company: str
    location: Optional[str]
    url: str
    source: str = "linkedin_lite"


@dataclass
class ChallengeStop:
    connector: str
    challenge_type: str
    disabled_until: str
    screenshot_path: Optional[str] = None


def linkedin_mode(store: Optional[AggregationStore] = None) -> str:
    """Default LITE unless config_audit opted into FULL."""
    env = (os.environ.get("LINKEDIN_BROWSER_MODE") or "").strip().upper()
    if env in (MODE_LITE, MODE_FULL):
        if env == MODE_FULL and store is not None:
            # FULL still requires audit trail
            if not _has_full_opt_in(store):
                return MODE_LITE
        return env
    if store is None:
        return MODE_LITE
    return MODE_FULL if _has_full_opt_in(store) else MODE_LITE


def _has_full_opt_in(store: AggregationStore) -> bool:
    with store._connect() as conn:
        row = conn.execute(
            """
            SELECT value FROM config_audit
            WHERE key=? AND value=?
            ORDER BY id DESC LIMIT 1
            """,
            (CONFIG_KEY_LINKEDIN_MODE, MODE_FULL),
        ).fetchone()
    return bool(row)


def enable_linkedin_full(store: AggregationStore, *, actor: str = "operator") -> None:
    store.audit_config(CONFIG_KEY_LINKEDIN_MODE, MODE_FULL, actor=actor)


def enable_linkedin_lite(store: AggregationStore, *, actor: str = "operator") -> None:
    store.audit_config(CONFIG_KEY_LINKEDIN_MODE, MODE_LITE, actor=actor)


def is_connector_disabled(store: AggregationStore, connector: str = "linkedin") -> bool:
    key = f"{CONFIG_KEY_DISABLED_UNTIL}:{connector}"
    with store._connect() as conn:
        row = conn.execute(
            "SELECT value FROM config_audit WHERE key=? ORDER BY id DESC LIMIT 1",
            (key,),
        ).fetchone()
    if not row or not row["value"]:
        return False
    try:
        until = datetime.fromisoformat(str(row["value"]).replace("Z", "+00:00"))
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < until
    except ValueError:
        return False


def handle_challenge_stop(
    store: AggregationStore,
    *,
    connector: str,
    challenge_type: str,
    screenshot_path: Optional[str] = None,
    source_id: Optional[str] = None,
) -> ChallengeStop:
    """Challenge law: bump fetch_err, self-disable 24h, record screenshot event."""
    until = (
        datetime.now(timezone.utc) + timedelta(hours=CHALLENGE_DISABLE_HOURS)
    ).replace(microsecond=0).isoformat()
    key = f"{CONFIG_KEY_DISABLED_UNTIL}:{connector}"
    store.audit_config(key, until, actor=f"challenge:{challenge_type}")
    sid = source_id or f"browser:{connector}"
    store.bump_board_health(sid, ats_type=connector, fetch_attempts=1, fetch_err=1)
    store.record_drop(
        reason="challenge_stop",
        source_id=sid,
        detail=f"{challenge_type}; screenshot={screenshot_path or 'none'}; until={until}",
    )
    store.record_cycle(
        f"challenge-{connector}-{utc_now_iso()}",
        "challenge_screenshot",
        {
            "connector": connector,
            "challenge_type": challenge_type,
            "screenshot_path": screenshot_path,
            "disabled_until": until,
        },
    )
    return ChallengeStop(
        connector=connector,
        challenge_type=challenge_type,
        disabled_until=until,
        screenshot_path=screenshot_path,
    )


def classify_parse_count(card_count: int, *, connector: str = "naukri") -> Optional[str]:
    """Selector-pack parse-minimum: <5 cards → F3 event reason, not silent empty."""
    if card_count < PARSE_MINIMUM_CARDS:
        return f"parse_below_minimum:{SELECTOR_PACK_VERSION}:{card_count}"
    return None


def leads_to_registry_candidates(leads: List[DiscoveryLead]) -> List[Dict[str, Any]]:
    """Map Lite discovery leads into probe-before-trust candidates (ATS URL preferred)."""
    out: List[Dict[str, Any]] = []
    for lead in leads:
        out.append(
            {
                "company": lead.company,
                "title": lead.title,
                "location": lead.location,
                "url": lead.url,
                "source": lead.source,
                "needs_probe": True,
            }
        )
    return out


def save_challenge_screenshot(raw: bytes, *, connector: str, dest_dir: Optional[Path] = None) -> str:
    dest = Path(dest_dir) if dest_dir else Path(__file__).resolve().parents[1] / "runtime" / "challenges"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{connector}_{utc_now_iso().replace(':', '')}.png"
    path.write_bytes(raw)
    return str(path)
