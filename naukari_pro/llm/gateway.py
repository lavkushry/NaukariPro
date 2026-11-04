"""
LLM Gateway — every call is:
  registry render → cache lookup → (optional) live call via ProviderRouter → schema validate → ledger.

Modes: record | replay | replay_preferred | live

Provider switching is config/env only (`AI_GATEWAY_DEFAULT_PROVIDER`, `config/ai_gateway.yml`).
When budget is paused/exceeded, live calls raise BudgetPaused/BudgetExceeded so pipelines
can degrade to deterministic-only without blocking search loops.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from naukari_pro.llm.cache import ResponseCache
from naukari_pro.llm.client import LLMClientError, OpenAICompatibleClient
from naukari_pro.llm.ledger import (
    BudgetExceeded,
    BudgetPaused,
    SpendEntry,
    SpendLedger,
    estimate_cost,
)
from naukari_pro.llm.provider_router import ProviderRouter
from naukari_pro.llm.registry import PromptRegistry
from naukari_pro.llm.routing import GatewayConfig
from naukari_pro.llm.validator import ValidationError, load_schema, parse_json_content, validate_response


# Map prompt_id → gateway task name (for per-task routing)
PROMPT_TASK_MAP = {
    "P1_jd_structure": "jd_extract",
    "P2_fit_score": "match_score",
    "P3_resume_tailor": "resume_tailor",
    "P4_application_answers": "answer_draft",
    "P5_cover_letter": "cover_letter",
}


@dataclass
class LLMResponse:
    prompt_id: str
    prompt_version: str
    input_hash: str
    data: Dict[str, Any]
    model: str
    provider: str
    cached: bool
    cost_usd: float
    input_tokens: int
    output_tokens: int
    validated: bool = True
    validation_errors: list = field(default_factory=list)
    task: str = ""


class LLMGateway:
    def __init__(
        self,
        *,
        registry: Optional[PromptRegistry] = None,
        client: Optional[OpenAICompatibleClient] = None,
        ledger: Optional[SpendLedger] = None,
        cache: Optional[ResponseCache] = None,
        mode: Optional[str] = None,
        router: Optional[ProviderRouter] = None,
        gateway_config: Optional[GatewayConfig] = None,
    ) -> None:
        self.registry = registry or PromptRegistry()
        defaults = self.registry.defaults
        self.gateway_config = gateway_config or GatewayConfig()
        self.router = router or ProviderRouter(config=self.gateway_config)
        # Legacy client kept for status / tests that inject BoomClient
        self.client = client or OpenAICompatibleClient()
        root = Path(__file__).resolve().parents[1]
        ledger_path = root / str(defaults.get("ledger_path") or "llm_spend_ledger.jsonl")
        cache_dir = root / str(defaults.get("cache_dir") or ".llm_cache")
        self.ledger = ledger or SpendLedger(
            path=ledger_path,
            monthly_cap_usd=float(
                self.gateway_config.monthly_cap_usd
                or defaults.get("monthly_cap_usd")
                or 25.0
            ),
            alert_at_usd=float(defaults.get("alert_at_usd") or 20.0),
            daily_cap_usd=self.gateway_config.daily_cap_usd,
            paused_budget=self.gateway_config.paused_budget,
        )
        self.cache = cache or ResponseCache(cache_dir=cache_dir)
        self.mode = (
            mode
            or os.environ.get("NAUKARI_LLM_MODE")
            or str(defaults.get("record_replay_mode") or "replay_preferred")
        ).lower()

    def task_for_prompt(self, prompt_id: str) -> str:
        return PROMPT_TASK_MAP.get(prompt_id, prompt_id)

    def status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "default_provider": self.gateway_config.default_provider,
            "available_providers": self.router.available(),
            "tasks": list((self.gateway_config.raw.get("tasks") or {}).keys()),
            "ledger": self.ledger.summary(),
            "prompts": self.registry.list_ids(),
        }

    def call(
        self,
        prompt_id: str,
        variables: Dict[str, Any],
        *,
        force_live: bool = False,
        task: Optional[str] = None,
    ) -> LLMResponse:
        spec, rendered = self.registry.render(prompt_id, variables)
        schema = load_schema(spec.schema_path)
        schema_name = spec.schema_path.name if spec.schema_path else ""
        input_hash = self.registry.input_hash(spec.prompt_version_key, rendered, schema_name)
        task_name = task or self.task_for_prompt(prompt_id)

        mode = "live" if force_live else self.mode
        cached_hit = self.cache.get(spec.prompt_version_key, input_hash)

        if mode == "replay":
            if not cached_hit:
                raise FileNotFoundError(
                    f"Replay cache miss for {spec.prompt_version_key} hash={input_hash[:12]}"
                )
            return self._from_cache(spec.prompt_id, spec.version, input_hash, cached_hit, task_name)

        if mode == "replay_preferred" and cached_hit and not force_live:
            return self._from_cache(spec.prompt_id, spec.version, input_hash, cached_hit, task_name)

        # live / record / replay_preferred miss
        try:
            self.ledger.ensure_budget(upcoming_cost=0.01)
        except (BudgetExceeded, BudgetPaused) as exc:
            self.ledger.record(
                SpendEntry(
                    ts=datetime.now(timezone.utc).isoformat(),
                    prompt_id=spec.prompt_id,
                    prompt_version=spec.version,
                    model="none",
                    provider="none",
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    cached=False,
                    input_hash=input_hash,
                    status="paused" if isinstance(exc, BudgetPaused) else "capped",
                    task=task_name,
                )
            )
            raise

        messages = [
            {"role": "system", "content": "Return valid JSON only. Never invent facts."},
            {"role": "user", "content": rendered},
        ]
        try:
            raw = self._complete_live(
                task_name,
                messages,
                temperature=spec.temperature,
                json_schema=schema,
            )
        except (LLMClientError, BudgetExceeded, BudgetPaused, RuntimeError) as exc:
            self.ledger.record(
                SpendEntry(
                    ts=datetime.now(timezone.utc).isoformat(),
                    prompt_id=spec.prompt_id,
                    prompt_version=spec.version,
                    model="none",
                    provider="none",
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    cached=False,
                    input_hash=input_hash,
                    status="error",
                    task=task_name,
                )
            )
            if isinstance(exc, (BudgetExceeded, BudgetPaused, LLMClientError)):
                raise
            raise LLMClientError(str(exc)) from exc

        try:
            data = parse_json_content(raw.content)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"LLM returned non-JSON: {exc}") from exc

        ok, errs = validate_response(data, schema)
        if not ok:
            raise ValidationError(f"Schema validation failed: {errs}")

        model_key = f"{raw.provider}/{raw.model}"
        cost = estimate_cost(model_key, raw.input_tokens, raw.output_tokens)
        self.ledger.ensure_budget(upcoming_cost=cost)

        latency_ms = int(getattr(raw, "latency_ms", 0) or 0)
        payload = {
            "data": data,
            "model": raw.model,
            "provider": raw.provider,
            "input_tokens": raw.input_tokens,
            "output_tokens": raw.output_tokens,
            "cost_usd": cost,
            "prompt_id": spec.prompt_id,
            "prompt_version": spec.version,
            "input_hash": input_hash,
            "task": task_name,
        }
        if mode in ("record", "live", "replay_preferred"):
            self.cache.put(spec.prompt_version_key, input_hash, payload)

        self.ledger.record(
            SpendEntry(
                ts=datetime.now(timezone.utc).isoformat(),
                prompt_id=spec.prompt_id,
                prompt_version=spec.version,
                model=raw.model,
                provider=raw.provider,
                input_tokens=raw.input_tokens,
                output_tokens=raw.output_tokens,
                cost_usd=cost,
                cached=False,
                input_hash=input_hash,
                status="ok",
                task=task_name,
                latency_ms=latency_ms,
            )
        )
        return LLMResponse(
            prompt_id=spec.prompt_id,
            prompt_version=spec.version,
            input_hash=input_hash,
            data=data,
            model=raw.model,
            provider=raw.provider,
            cached=False,
            cost_usd=cost,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            validated=True,
            task=task_name,
        )

    def _complete_live(
        self,
        task: str,
        messages: list,
        *,
        temperature: float,
        json_schema: Optional[Dict[str, Any]],
    ):
        """Prefer ProviderRouter; fall back to injected legacy client for tests."""
        # If tests injected a non-default client without router providers, use client.
        if self.client is not None and type(self.client).__name__ != "OpenAICompatibleClient":
            return self.client.complete(
                messages,
                temperature=temperature,
                json_schema=json_schema,
            )
        if self.router.available():
            return self.router.complete_task(
                task,
                messages,
                json_schema=json_schema,
                temperature=temperature,
            )
        return self.client.complete(
            messages,
            temperature=temperature,
            json_schema=json_schema,
        )

    def _from_cache(
        self,
        prompt_id: str,
        version: str,
        input_hash: str,
        cached_hit: Dict[str, Any],
        task_name: str = "",
    ) -> LLMResponse:
        data = cached_hit["data"]
        spec = self.registry.get(prompt_id)
        schema = load_schema(spec.schema_path)
        ok, errs = validate_response(data, schema)
        if not ok:
            raise ValidationError(f"Cached response failed validation: {errs}")
        self.ledger.record(
            SpendEntry(
                ts=datetime.now(timezone.utc).isoformat(),
                prompt_id=prompt_id,
                prompt_version=version,
                model=str(cached_hit.get("model") or "cache"),
                provider=str(cached_hit.get("provider") or "cache"),
                input_tokens=int(cached_hit.get("input_tokens") or 0),
                output_tokens=int(cached_hit.get("output_tokens") or 0),
                cost_usd=0.0,  # replay does not re-bill
                cached=True,
                input_hash=input_hash,
                status="ok",
                task=task_name or str(cached_hit.get("task") or ""),
            )
        )
        return LLMResponse(
            prompt_id=prompt_id,
            prompt_version=version,
            input_hash=input_hash,
            data=data,
            model=str(cached_hit.get("model") or "cache"),
            provider=str(cached_hit.get("provider") or "cache"),
            cached=True,
            cost_usd=0.0,
            input_tokens=int(cached_hit.get("input_tokens") or 0),
            output_tokens=int(cached_hit.get("output_tokens") or 0),
            validated=True,
            validation_errors=errs,
            task=task_name or str(cached_hit.get("task") or ""),
        )
