"""OpenAI-compatible client with cheap-model-first fallback chain."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class ModelEndpoint:
    provider: str
    model: str
    base_url: str
    api_key_env: str

    @property
    def model_key(self) -> str:
        return f"{self.provider}/{self.model}"


# Groq free → Gemini flash → paid OpenAI
DEFAULT_CHAIN: List[ModelEndpoint] = [
    ModelEndpoint(
        provider="groq",
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
    ),
    ModelEndpoint(
        provider="gemini",
        model="gemini-2.0-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GEMINI_API_KEY",
    ),
    ModelEndpoint(
        provider="openai",
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    ),
]


@dataclass
class RawCompletion:
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    raw: Dict[str, Any]


class LLMClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self, chain: Optional[Sequence[ModelEndpoint]] = None) -> None:
        self.chain = list(chain) if chain else list(DEFAULT_CHAIN)

    def available_chain(self) -> List[ModelEndpoint]:
        out = []
        for ep in self.chain:
            if os.environ.get(ep.api_key_env):
                out.append(ep)
        return out

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.0,
        json_schema: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> RawCompletion:
        errors: List[str] = []
        chain = self.available_chain()
        if not chain:
            raise LLMClientError(
                "No LLM API keys configured (set GROQ_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY)"
            )
        for ep in chain:
            try:
                return self._call(ep, messages, temperature=temperature, json_schema=json_schema, timeout=timeout)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{ep.model_key}: {exc}")
                continue
        raise LLMClientError("All model endpoints failed: " + " | ".join(errors))

    def _call(
        self,
        ep: ModelEndpoint,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        json_schema: Optional[Dict[str, Any]],
        timeout: float,
    ) -> RawCompletion:
        api_key = os.environ.get(ep.api_key_env, "")
        url = ep.base_url.rstrip("/") + "/chat/completions"
        body: Dict[str, Any] = {
            "model": ep.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "naukari_pro_schema",
                    "schema": json_schema,
                    "strict": True,
                },
            }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            # Some providers reject json_schema; retry once without it
            if json_schema and e.code in (400, 422):
                return self._call(ep, messages, temperature=temperature, json_schema=None, timeout=timeout)
            raise LLMClientError(f"HTTP {e.code}: {detail[:300]}") from e

        choices = payload.get("choices") or []
        if not choices:
            raise LLMClientError("empty choices")
        content = choices[0].get("message", {}).get("content") or ""
        usage = payload.get("usage") or {}
        return RawCompletion(
            content=content,
            model=ep.model,
            provider=ep.provider,
            input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
            raw=payload,
        )
