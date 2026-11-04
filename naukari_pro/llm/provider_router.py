"""Resolve provider chain for a task and execute with fallbacks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from naukari_pro.llm.providers import LLMResponse, OpenAICompatibleProvider, build_providers_from_env
from naukari_pro.llm.routing import GatewayConfig, TaskRoute


class ProviderRouter:
    def __init__(
        self,
        *,
        config: Optional[GatewayConfig] = None,
        providers: Optional[Dict[str, OpenAICompatibleProvider]] = None,
    ) -> None:
        self.config = config or GatewayConfig()
        self.providers = providers if providers is not None else build_providers_from_env(self.config.raw)

    def available(self) -> List[str]:
        return [n for n, p in self.providers.items() if p.available()]

    def chain_for_task(self, task: str) -> Tuple[TaskRoute, List[str]]:
        route = self.config.task_route(task)
        names = [route.provider] + [f for f in route.fallbacks if f != route.provider]
        # Prefer providers that are actually configured
        ordered = [n for n in names if n in self.providers]
        # Append any remaining available providers as last-resort
        for n in self.available():
            if n not in ordered:
                ordered.append(n)
        return route, ordered

    def complete_task(
        self,
        task: str,
        messages: List[Dict[str, str]],
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
    ) -> LLMResponse:
        route, chain = self.chain_for_task(task)
        if not chain:
            raise RuntimeError(
                "No AI providers available — set AI_PROVIDER_*_API_KEY or GROQ_API_KEY"
            )
        errors: List[str] = []
        for name in chain:
            provider = self.providers.get(name)
            if not provider or not provider.available():
                continue
            model = model_override or (route.model if name == route.provider else provider.default_model)
            try:
                return provider.complete(
                    messages,
                    json_schema=json_schema,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model,
                    timeout=route.timeout_s,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")
                continue
        raise RuntimeError("All providers failed for task=%s: %s" % (task, " | ".join(errors)))
