"""Per-call + monthly/daily spend ledger with hard cap and SQLite dual-write."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from naukari_pro.llm.ai_calls_db import AICallsStore


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
    status: str  # ok | capped | error | blocked | paused
    task: str = ""
    latency_ms: int = 0
    request_id: str = ""


class BudgetExceeded(RuntimeError):
    pass


class BudgetPaused(RuntimeError):
    """Raised when paused_budget is on — callers should degrade to deterministic-only."""


# Rough public list prices (USD / 1M tokens) — used only for ledger estimates
PRICE_TABLE = {
    "groq/llama-3.3-70b-versatile": (0.59, 0.79),
    "groq/llama-3.1-8b-instant": (0.05, 0.08),
    "gemini/gemini-2.0-flash": (0.10, 0.40),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4o": (2.50, 10.00),
    "xai/grok-2-latest": (2.00, 10.00),
    "deepseek/deepseek-chat": (0.14, 0.28),
    "mistral/mistral-small-latest": (0.20, 0.60),
    "ollama/llama3.2": (0.0, 0.0),
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
        daily_cap_usd: float = 5.0,
        paused_budget: bool = False,
        sqlite_db: Optional[Path] = None,
        enable_sqlite: bool = True,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.path = Path(path) if path else root / "llm_spend_ledger.jsonl"
        self.monthly_cap_usd = float(
            os.environ.get("NAUKARI_LLM_MONTHLY_CAP", monthly_cap_usd)
        )
        self.alert_at_usd = float(os.environ.get("NAUKARI_LLM_ALERT_AT", alert_at_usd))
        self.daily_cap_usd = float(os.environ.get("AI_GATEWAY_DAILY_CAP", daily_cap_usd))
        env_paused = os.environ.get("AI_GATEWAY_PAUSED_BUDGET", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self.paused_budget = bool(paused_budget or env_paused)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.alerts: List[str] = []
        self._sqlite: Optional[AICallsStore] = None
        if enable_sqlite:
            try:
                self._sqlite = AICallsStore(sqlite_db)
            except Exception:  # noqa: BLE001
                self._sqlite = None

    def _month_prefix(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _day_prefix(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

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

    def day_spend(self) -> float:
        prefix = self._day_prefix()
        total = 0.0
        if self._sqlite is not None:
            try:
                return self._sqlite.day_spend(prefix)
            except Exception:  # noqa: BLE001
                pass
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

    def is_deterministic_only(self) -> bool:
        if self.paused_budget:
            return True
        spent = self.month_spend()
        day = self.day_spend()
        return (spent >= self.monthly_cap_usd) or (day >= self.daily_cap_usd)

    def ensure_budget(self, upcoming_cost: float = 0.0, *, soft: bool = False) -> None:
        if self.paused_budget:
            msg = "AI gateway paused_budget=true — deterministic-only mode"
            if msg not in self.alerts:
                self.alerts.append(msg)
            raise BudgetPaused(msg)
        spent = self.month_spend()
        day = self.day_spend()
        if spent >= self.alert_at_usd:
            msg = f"LLM spend alert: ${spent:.4f} >= alert ${self.alert_at_usd:.2f}"
            if msg not in self.alerts:
                self.alerts.append(msg)
        if day + upcoming_cost > self.daily_cap_usd:
            raise BudgetExceeded(
                f"Daily LLM cap ${self.daily_cap_usd:.2f} exceeded "
                f"(spent=${day:.4f}, upcoming=${upcoming_cost:.4f})"
            )
        if spent + upcoming_cost > self.monthly_cap_usd:
            raise BudgetExceeded(
                f"Monthly LLM cap ${self.monthly_cap_usd:.2f} exceeded "
                f"(spent=${spent:.4f}, upcoming=${upcoming_cost:.4f})"
            )

    def record(self, entry: SpendEntry) -> None:
        payload = asdict(entry)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if self._sqlite is not None and not entry.cached:
            try:
                self._sqlite.record(
                    ts=entry.ts,
                    task=entry.task or None,
                    prompt_id=entry.prompt_id,
                    prompt_version=entry.prompt_version,
                    provider=entry.provider,
                    model=entry.model,
                    tokens_in=entry.input_tokens,
                    tokens_out=entry.output_tokens,
                    cost_usd=entry.cost_usd,
                    latency_ms=entry.latency_ms,
                    request_id=entry.request_id or None,
                    input_hash=entry.input_hash,
                    status=entry.status,
                    cached=entry.cached,
                )
            except Exception:  # noqa: BLE001
                pass

    def summary(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "month": self._month_prefix(),
            "day": self._day_prefix(),
            "spent_usd": round(self.month_spend(), 6),
            "day_spent_usd": round(self.day_spend(), 6),
            "cap_usd": self.monthly_cap_usd,
            "daily_cap_usd": self.daily_cap_usd,
            "alert_at_usd": self.alert_at_usd,
            "paused_budget": self.paused_budget,
            "deterministic_only": self.is_deterministic_only(),
            "alerts": list(self.alerts),
            "ledger_path": str(self.path),
        }
        if self._sqlite is not None:
            out["sqlite"] = self._sqlite.summary()
        return out

