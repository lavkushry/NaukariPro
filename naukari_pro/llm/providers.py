"""Provider-agnostic LLM adapters (OpenAI-compatible + Anthropic Messages)."""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    raw: Dict[str, Any]
    latency_ms: int = 0


class LLMProvider(Protocol):
    name: str

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> LLMResponse:
        ...


def _env_key(*names: str) -> str:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return ""


class OpenAICompatibleProvider:
    """Works for OpenAI, Groq, Gemini OpenAI mode, xAI, DeepSeek, Mistral, Ollama, OpenRouter, compat."""

    def __init__(
        self,
        name: str,
        *,
        base_url: str,
        api_key: str,
        default_model: str,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model

    def available(self) -> bool:
        return bool(self.base_url and (self.api_key or self.name in ("ollama",)))

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> LLMResponse:
        url = self.base_url + "/chat/completions"
        body: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": 0.0 if temperature is None else temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if json_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "naukari_pro_schema",
                    "schema": json_schema,
                    "strict": True,
                },
            }
        return self._post(url, body, timeout=timeout, json_schema=json_schema)

    def _post(
        self,
        url: str,
        body: Dict[str, Any],
        *,
        timeout: float,
        json_schema: Optional[Dict[str, Any]],
        attempt: int = 0,
    ) -> LLMResponse:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                ra = e.headers.get("Retry-After") if e.headers else None
                try:
                    sleep_s = min(float(ra), 30.0) if ra else (1.5 * (2 ** attempt) + random.uniform(0, 0.5))
                except ValueError:
                    sleep_s = 1.5 * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                return self._post(url, body, timeout=timeout, json_schema=json_schema, attempt=attempt + 1)
            if json_schema and e.code in (400, 422):
                body2 = dict(body)
                body2.pop("response_format", None)
                return self._post(url, body2, timeout=timeout, json_schema=None, attempt=attempt)
            raise RuntimeError(f"{self.name} HTTP {e.code}: {detail[:300]}") from e

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"{self.name}: empty choices")
        content = choices[0].get("message", {}).get("content") or ""
        usage = payload.get("usage") or {}
        return LLMResponse(
            content=content,
            model=str(body.get("model") or self.default_model),
            provider=self.name,
            input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
            raw=payload,
            latency_ms=int((time.time() - t0) * 1000),
        )


class AnthropicMessagesProvider:
    """Native Anthropic Messages API adapter (not OpenAI-compatible)."""

    def __init__(
        self,
        name: str = "anthropic",
        *,
        api_key: str,
        default_model: str,
        base_url: str = "https://api.anthropic.com",
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = base_url.rstrip("/")

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> LLMResponse:
        system = ""
        converted = []
        for m in messages:
            role = m.get("role") or "user"
            content = m.get("content") or ""
            if role == "system":
                system = (system + "\n" + content).strip() if system else content
            else:
                converted.append({"role": "user" if role != "assistant" else "assistant", "content": content})
        if json_schema and system:
            system += "\nRespond with only valid JSON matching the required schema."
        elif json_schema:
            system = "Respond with only valid JSON matching the required schema."
        body: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": converted or [{"role": "user", "content": ""}],
            "max_tokens": int(max_tokens or 2048),
            "temperature": 0.0 if temperature is None else temperature,
        }
        if system:
            body["system"] = system
        data = json.dumps(body).encode("utf-8")
        url = self.base_url + "/v1/messages"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("x-api-key", self.api_key)
        req.add_header("anthropic-version", "2023-06-01")
        req.add_header("Content-Type", "application/json")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(1.5 + random.uniform(0, 0.5))
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            else:
                raise RuntimeError(f"anthropic HTTP {e.code}: {detail[:300]}") from e
        blocks = payload.get("content") or []
        content = ""
        for b in blocks:
            if isinstance(b, dict) and b.get("type") == "text":
                content += b.get("text") or ""
        usage = payload.get("usage") or {}
        return LLMResponse(
            content=content,
            model=str(body.get("model") or self.default_model),
            provider=self.name,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            raw=payload,
            latency_ms=int((time.time() - t0) * 1000),
        )


def build_providers_from_env(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Instantiate configured providers that have credentials (or ollama)."""
    out: Dict[str, Any] = {}
    providers = cfg.get("providers") or {}
    for name, meta in providers.items():
        if not isinstance(meta, dict):
            continue
        if name == "compat":
            base = os.environ.get(str(meta.get("base_url_env") or ""), "").rstrip("/")
            key = _env_key(str(meta.get("api_key_env") or ""))
            model = os.environ.get(str(meta.get("default_model_env") or ""), "local-model")
            if not base:
                continue
            out[name] = OpenAICompatibleProvider(name, base_url=base, api_key=key or "ollama", default_model=model)
            continue
        if name == "anthropic":
            key = _env_key(str(meta.get("api_key_env") or ""), "ANTHROPIC_API_KEY")
            if not key:
                continue
            model = str(meta.get("default_model") or "claude-sonnet-4-20250514")
            out[name] = AnthropicMessagesProvider(
                name="anthropic",
                api_key=key,
                default_model=model,
                base_url=str(meta.get("base_url") or "https://api.anthropic.com"),
            )
            continue
        base = str(meta.get("base_url") or "").rstrip("/")
        key_env = str(meta.get("api_key_env") or "")
        # Legacy aliases
        legacy = {
            "AI_PROVIDER_GROQ_API_KEY": "GROQ_API_KEY",
            "AI_PROVIDER_OPENAI_API_KEY": "OPENAI_API_KEY",
            "AI_PROVIDER_GEMINI_API_KEY": "GEMINI_API_KEY",
            "AI_PROVIDER_XAI_API_KEY": "XAI_API_KEY",
        }
        key = _env_key(key_env, legacy.get(key_env, ""))
        model = str(meta.get("default_model") or "unknown")
        if name == "ollama":
            out[name] = OpenAICompatibleProvider(name, base_url=base or "http://127.0.0.1:11434/v1", api_key=key or "ollama", default_model=model)
            continue
        if not key or not base:
            continue
        out[name] = OpenAICompatibleProvider(name, base_url=base, api_key=key, default_model=model)
    return out
