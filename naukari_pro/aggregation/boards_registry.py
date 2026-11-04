"""
boards.csv registry (jobseek schema) — import/export for AggregationStore sources.

Columns: company_slug, board_slug, board_url, monitor_type, monitor_config (JSON), scraper_type
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.storage import AggregationStore

DEFAULT_BOARDS_CSV = Path(__file__).resolve().parents[2] / "config" / "boards.csv"


def _parse_monitor_config(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        return {"raw": raw}


def row_to_source(row: Dict[str, str]) -> Dict[str, Any]:
    company_slug = (row.get("company_slug") or row.get("company") or "").strip()
    board_slug = (row.get("board_slug") or row.get("board_identifier") or "").strip()
    scraper = (row.get("scraper_type") or row.get("ats_type") or "generic").strip().lower()
    board_url = (row.get("board_url") or "").strip()
    monitor_type = (row.get("monitor_type") or "json_api").strip()
    monitor_config = _parse_monitor_config(row.get("monitor_config") or "")
    if not board_slug and board_url:
        board_slug = board_url.rstrip("/").split("/")[-1]
    if not company_slug:
        company_slug = board_slug or "unknown"
    source_id = f"{scraper}:{board_slug}".lower()
    return {
        "source_id": source_id,
        "company": company_slug.replace("-", " ").replace("_", " ").title(),
        "ats_type": scraper,
        "board_identifier": board_slug,
        "domain": board_url or None,
        "active": True,
        "monitor_type": monitor_type,
        "monitor_config": monitor_config,
        "company_slug": company_slug,
        "board_url": board_url,
    }


def load_boards_csv(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = Path(path) if path else DEFAULT_BOARDS_CSV
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not row:
                continue
            src = row_to_source({k: (v or "") for k, v in row.items()})
            if src.get("board_identifier"):
                out.append(src)
    return out


def import_boards_csv(
    path: Optional[Path] = None,
    *,
    store: Optional[AggregationStore] = None,
) -> int:
    store = store or AggregationStore()
    rows = load_boards_csv(path)
    for src in rows:
        store.upsert_source(
            {
                "source_id": src["source_id"],
                "company": src["company"],
                "ats_type": src["ats_type"],
                "board_identifier": src["board_identifier"],
                "domain": src.get("domain"),
                "active": True,
            }
        )
    return len(rows)


def export_boards_csv(
    path: Optional[Path] = None,
    *,
    store: Optional[AggregationStore] = None,
) -> Path:
    store = store or AggregationStore()
    path = Path(path) if path else DEFAULT_BOARDS_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    sources = store.list_active_sources(include_quiet_every_n=1, cycle=0)
    fieldnames = [
        "company_slug",
        "board_slug",
        "board_url",
        "monitor_type",
        "monitor_config",
        "scraper_type",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for s in sources:
            company = (s.get("company") or "").lower().replace(" ", "-")
            board = s.get("board_identifier") or ""
            ats = s.get("ats_type") or "generic"
            writer.writerow(
                {
                    "company_slug": company,
                    "board_slug": board,
                    "board_url": s.get("domain") or "",
                    "monitor_type": "json_api",
                    "monitor_config": json.dumps({"source_id": s.get("source_id")}),
                    "scraper_type": ats,
                }
            )
    return path
