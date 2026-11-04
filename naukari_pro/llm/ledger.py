"""Per-call + monthly spend ledger with hard cap."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SpendEntry:
    ts: str
    prompt_id: str
    prompt_version: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool
    input_hash: str
    status: str  # ok | capped | error | blocked


class BudgetExceeded(RuntimeError):
    pass


# Rough public list prices (USD / 1M tokens) — used only for ledger estimates
PRICE_TABLE = {
    "groq/llama-3.3-70b-versatile": (0.59, 0.79),
    "groq/llama-3.1-8b-instant": (0.05, 0.08),
    "gemini/gemini-2.0-flash": (0.10, 0.40),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.50, 10.00),
}


def estimate_cost(model_key: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = PRICE_TABLE.get(model_key, (1.0, 3.0))
    return (input_tokens / 1_000_000.0) * inp + (output_tokens / 1_000_000.0) * out


class SpendLedger:
    def __init__(
        self,
        path: Optional[Path] = None,
        *,
        monthly_cap_usd: float = 25.0,
        alert_at_usd: float = 20.0,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.path = Path(path) if path else root / "llm_spend_ledger.jsonl"
        self.monthly_cap_usd = float(
            os.environ.get("NAUKARI_LLM_MONTHLY_CAP", monthly_cap_usd)
        )
        self.alert_at_usd = float(os.environ.get("NAUKARI_LLM_ALERT_AT", alert_at_usd))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.alerts: List[str] = []

    def _month_prefix(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def month_spend(self) -> float:
        prefix = self._month_prefix()
        total = 0.0
        if not self.path.exists():
            return 0.0
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(row.get("ts", "")).startswith(prefix):
                    total += float(row.get("cost_usd") or 0.0)
        return total

    def ensure_budget(self, upcoming_cost: float = 0.0) -> None:
        spent = self.month_spend()
        if spent >= self.alert_at_usd:
            msg = f"LLM spend alert: ${spent:.4f} >= alert ${self.alert_at_usd:.2f}"
            if msg not in self.alerts:
                self.alerts.append(msg)
        if spent + upcoming_cost > self.monthly_cap_usd:
            raise BudgetExceeded(
                f"Monthly LLM cap ${self.monthly_cap_usd:.2f} exceeded "
                f"(spent=${spent:.4f}, upcoming=${upcoming_cost:.4f})"
            )

    def record(self, entry: SpendEntry) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def summary(self) -> Dict[str, Any]:
        return {
            "month": self._month_prefix(),
            "spent_usd": round(self.month_spend(), 6),
            "cap_usd": self.monthly_cap_usd,
            "alert_at_usd": self.alert_at_usd,
            "alerts": list(self.alerts),
            "ledger_path": str(self.path),
        }
