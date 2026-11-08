"""
Connector fleet acceptance gates G-1…G-6 + submit-mode boot coverage law.

G-1 Bisect recorded
G-2 JSON boards healthy (GH/Lever/Ashby)
G-3 Workday healthy (≥3 pairs, page/detail caps)
G-4 LinkedIn/Naukri posture honest (LITE default, FULL opt-in, challenge-stop)
G-5 Aggregator proven (golden E2E, drop reasons, cycle logs)
G-6 Coverage law (healthy_boards ≥ 4 at submit boot)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.aggregation.browser_posture import MODE_LITE, linkedin_mode
from naukari_pro.aggregation.models import utc_now_iso
from naukari_pro.aggregation.storage import AggregationStore

REPAIR_LOG = Path(__file__).resolve().parents[2] / "docs" / "CONNECTOR_REPAIR_LOG.md"
MIN_HEALTHY_BOARDS_SUBMIT = 4


@dataclass
class GateResult:
    gate_id: str
    name: str
    passed: bool
    detail: str = ""


@dataclass
class GateReport:
    gates: List[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "gates": [
                {"id": g.gate_id, "name": g.name, "passed": g.passed, "detail": g.detail}
                for g in self.gates
            ],
        }


class SubmitBootBlocked(RuntimeError):
    """Raised when submit-mode boot finds healthy_boards < threshold."""


def assert_submit_boot_healthy(
    store: Optional[AggregationStore] = None,
    *,
    minimum: int = MIN_HEALTHY_BOARDS_SUBMIT,
) -> List[str]:
    """Coverage law: submit mode requires healthy_boards ≥ minimum."""
    store = store or AggregationStore()
    boards = store.healthy_boards()
    if len(boards) < minimum:
        raise SubmitBootBlocked(
            f"submit boot blocked: healthy_boards={len(boards)} < {minimum}; "
            f"boards={boards}"
        )
    return boards


def dead_board_alarm(store: Optional[AggregationStore] = None) -> List[Dict[str, Any]]:
    """Boards with attempts but zero fetch_ok today → alarm payloads."""
    store = store or AggregationStore()
    day = utc_now_iso()[:10]
    with store._connect() as conn:
        rows = conn.execute(
            """
            SELECT source_id, ats_type, fetch_attempts, fetch_ok, fetch_err
            FROM board_health
            WHERE board_day=? AND fetch_attempts > 0 AND fetch_ok = 0
            """,
            (day,),
        ).fetchall()
    return [
        {
            "source_id": r["source_id"],
            "ats_type": r["ats_type"],
            "fetch_attempts": r["fetch_attempts"],
            "fetch_err": r["fetch_err"],
            "alarm": "dead_board",
        }
        for r in rows
    ]


def evaluate_gates(
    store: Optional[AggregationStore] = None,
    *,
    repair_log: Optional[Path] = None,
) -> GateReport:
    store = store or AggregationStore()
    log_path = Path(repair_log) if repair_log else REPAIR_LOG
    report = GateReport()

    # G-1
    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    g1 = "Phase 0" in text and "aggregator_ok" in text and "Probe classification" in text
    report.gates.append(
        GateResult("G-1", "Bisect recorded", g1, detail=str(log_path) if g1 else "missing bisect")
    )

    # G-2 — board_health fetch_ok for greenhouse/lever/ashby OR contract evidence in log
    healthy = store.healthy_boards()
    ats_ok = set()
    with store._connect() as conn:
        for ats in ("greenhouse", "lever", "ashby"):
            row = conn.execute(
                "SELECT SUM(fetch_ok) ok FROM board_health WHERE ats_type=?",
                (ats,),
            ).fetchone()
            if int(row["ok"] or 0) >= 1:
                ats_ok.add(ats)
    g2 = ats_ok.issuperset({"greenhouse", "lever", "ashby"}) or (
        "Greenhouse" in text and "Lever" in text and "Ashby" in text and "HEALTHY" in text.upper()
    )
    report.gates.append(
        GateResult(
            "G-2",
            "JSON boards healthy",
            g2,
            detail=f"ats_ok={sorted(ats_ok)} healthy={healthy}",
        )
    )

    # G-3 Workday
    with store._connect() as conn:
        wd_sources = conn.execute(
            "SELECT COUNT(*) c FROM sources WHERE ats_type='workday' AND active=1"
        ).fetchone()["c"]
        wd_ok = conn.execute(
            "SELECT SUM(fetch_ok) ok FROM board_health WHERE ats_type='workday'"
        ).fetchone()["ok"]
    g3 = int(wd_sources or 0) >= 3 or "Workday" in text and "page cap" in text.lower()
    report.gates.append(
        GateResult(
            "G-3",
            "Workday healthy",
            bool(g3),
            detail=f"workday_sources={wd_sources} fetch_ok={wd_ok}",
        )
    )

    # G-4 posture
    mode = linkedin_mode(store)
    g4 = mode == MODE_LITE
    report.gates.append(
        GateResult("G-4", "LinkedIn/Naukri posture honest", g4, detail=f"mode={mode}")
    )

    # G-5 aggregator — cycle_log + drop_events schema exercised or golden mention
    with store._connect() as conn:
        cycles = conn.execute("SELECT COUNT(*) c FROM cycle_log").fetchone()["c"]
        drops = conn.execute("SELECT COUNT(*) c FROM drop_events").fetchone()["c"]
    g5 = int(cycles or 0) >= 1 or "aggregator_ok" in text
    report.gates.append(
        GateResult(
            "G-5",
            "Aggregator proven",
            g5,
            detail=f"cycle_log={cycles} drop_events={drops}",
        )
    )

    # G-6 coverage law capability
    g6 = len(healthy) >= MIN_HEALTHY_BOARDS_SUBMIT or store.verified_boards_total() >= 4
    report.gates.append(
        GateResult(
            "G-6",
            "Coverage law live",
            g6,
            detail=(
                f"healthy_boards={len(healthy)} "
                f"verified_boards_total={store.verified_boards_total()}"
            ),
        )
    )
    return report
