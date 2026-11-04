"""Load ai_gateway.yml and resolve per-task provider chains."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = ROOT / "config" / "ai_gateway.yml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        return _minimal_yaml(text)


def _minimal_yaml(text: str) -> Dict[str, Any]:
    """Enough for our flat-ish gateway file when PyYAML is missing."""
    # Prefer installing pyyaml; fallback returns empty and callers use defaults
    data: Dict[str, Any] = {"providers": {}, "tasks": {}, "default_provider": "groq"}
    section = None
    current_task = None
    current_prov = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("default_provider:"):
            data["default_provider"] = line.split(":", 1)[1].strip()
        elif line.startswith("daily_cap_usd:"):
            try:
                data["daily_cap_usd"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("monthly_cap_usd:"):
            try:
                data["monthly_cap_usd"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line == "providers:":
            section = "providers"
            current_task = current_prov = None
        elif line == "tasks:":
            section = "tasks"
            current_task = current_prov = None
        elif section == "providers" and line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            current_prov = line.strip().rstrip(":")
            data["providers"][current_prov] = {}
        elif section == "providers" and current_prov and line.startswith("    "):
            k, _, v = line.strip().partition(":")
            data["providers"][current_prov][k.strip()] = v.strip()
        elif section == "tasks" and line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            current_task = line.strip().rstrip(":")
            data["tasks"][current_task] = {}
        elif section == "tasks" and current_task and line.startswith("    "):
            k, _, v = line.strip().partition(":")
            val = v.strip()
            if k.strip() == "fallbacks":
                inner = val.strip("[]")
                data["tasks"][current_task]["fallbacks"] = [x.strip() for x in inner.split(",") if x.strip()]
            else:
                data["tasks"][current_task][k.strip()] = val
    return data


@dataclass
class TaskRoute:
    task: str
    provider: str
    model: str
    fallbacks: List[str] = field(default_factory=list)
    timeout_s: float = 60.0
    max_cost_usd: float = 0.05
    prompt_id: Optional[str] = None


class GatewayConfig:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_YAML
        self.raw: Dict[str, Any] = _load_yaml(self.path) if self.path.exists() else {}
        env_default = os.environ.get("AI_GATEWAY_DEFAULT_PROVIDER")
        if env_default:
            self.raw["default_provider"] = env_default

    @property
    def default_provider(self) -> str:
        return str(self.raw.get("default_provider") or "groq")

    @property
    def daily_cap_usd(self) -> float:
        return float(os.environ.get("AI_GATEWAY_DAILY_CAP", self.raw.get("daily_cap_usd") or 5.0))

    @property
    def monthly_cap_usd(self) -> float:
        return float(os.environ.get("NAUKARI_LLM_MONTHLY_CAP", self.raw.get("monthly_cap_usd") or 25.0))

    @property
    def paused_budget(self) -> bool:
        if os.environ.get("AI_GATEWAY_PAUSED_BUDGET", "").lower() in ("1", "true", "yes"):
            return True
        return bool(self.raw.get("paused_budget"))

    def task_route(self, task: str) -> TaskRoute:
        tasks = self.raw.get("tasks") or {}
        meta = dict(tasks.get(task) or {})
        # Per-task env override: AI_GATEWAY_<TASK>_PROVIDER
        env_prov = os.environ.get(f"AI_GATEWAY_{task.upper()}_PROVIDER")
        provider = env_prov or str(meta.get("provider") or self.default_provider)
        model = str(meta.get("model") or "")
        providers = self.raw.get("providers") or {}
        if not model and provider in providers:
            model = str((providers[provider] or {}).get("default_model") or "")
        fallbacks = meta.get("fallbacks") or []
        if isinstance(fallbacks, str):
            fallbacks = [x.strip() for x in fallbacks.strip("[]").split(",") if x.strip()]
        try:
            timeout_s = float(meta.get("timeout_s") or 60)
        except (TypeError, ValueError):
            timeout_s = 60.0
        try:
            max_cost = float(meta.get("max_cost_usd") or 0.05)
        except (TypeError, ValueError):
            max_cost = 0.05
        return TaskRoute(
            task=task,
            provider=provider,
            model=model,
            fallbacks=list(fallbacks),
            timeout_s=timeout_s,
            max_cost_usd=max_cost,
            prompt_id=meta.get("prompt_id"),
        )
