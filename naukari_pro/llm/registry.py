"""Versioned prompt registry backed by PROMPT_VERSIONS.yaml."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

LLM_ROOT = Path(__file__).resolve().parent
PROMPT_VERSIONS_PATH = LLM_ROOT / "PROMPT_VERSIONS.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        # Minimal fallback parser for our flat structure
        return _minimal_yaml(text)


def _minimal_yaml(text: str) -> Dict[str, Any]:
    """Tiny subset parser so tests work without PyYAML."""
    data: Dict[str, Any] = {"prompts": {}, "defaults": {}}
    section = None
    current: Optional[str] = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line == "prompts:":
            section = "prompts"
            continue
        if line == "defaults:":
            section = "defaults"
            current = None
            continue
        if section == "prompts" and re.match(r"^  [A-Za-z0-9_]+:\s*$", line):
            current = line.strip().rstrip(":")
            data["prompts"][current] = {}
            continue
        if section == "prompts" and current and re.match(r"^    \w+:", line):
            key, _, val = line.strip().partition(":")
            data["prompts"][current][key.strip()] = val.strip().strip('"').strip("'")
            continue
        if section == "defaults" and re.match(r"^  \w+:", line):
            key, _, val = line.strip().partition(":")
            v = val.strip().strip('"').strip("'")
            try:
                if "." in v:
                    data["defaults"][key] = float(v)
                else:
                    data["defaults"][key] = int(v) if v.isdigit() else v
            except ValueError:
                data["defaults"][key] = v
    return data


@dataclass(frozen=True)
class PromptSpec:
    prompt_id: str
    version: str
    file: Path
    schema_path: Optional[Path]
    temperature: float
    purpose: str

    @property
    def prompt_version_key(self) -> str:
        return f"{self.prompt_id}@{self.version}"


class PromptRegistry:
    def __init__(self, versions_path: Optional[Path] = None) -> None:
        self.versions_path = Path(versions_path) if versions_path else PROMPT_VERSIONS_PATH
        raw = _load_yaml(self.versions_path)
        self.defaults: Dict[str, Any] = raw.get("defaults") or {}
        self._prompts: Dict[str, PromptSpec] = {}
        for pid, meta in (raw.get("prompts") or {}).items():
            schema_rel = meta.get("schema")
            schema_path = (LLM_ROOT / schema_rel) if schema_rel else None
            temp = meta.get("temperature", 0)
            try:
                temp_f = float(temp)
            except (TypeError, ValueError):
                temp_f = 0.0
            self._prompts[pid] = PromptSpec(
                prompt_id=pid,
                version=str(meta.get("version") or "0.0.0"),
                file=LLM_ROOT / "prompts" / str(meta.get("file")),
                schema_path=schema_path,
                temperature=temp_f,
                purpose=str(meta.get("purpose") or ""),
            )

    def get(self, prompt_id: str) -> PromptSpec:
        if prompt_id not in self._prompts:
            raise KeyError(f"Prompt {prompt_id!r} not registered in PROMPT_VERSIONS.yaml")
        return self._prompts[prompt_id]

    def list_ids(self) -> list[str]:
        return sorted(self._prompts.keys())

    def render(self, prompt_id: str, variables: Dict[str, Any]) -> tuple[PromptSpec, str]:
        spec = self.get(prompt_id)
        if not spec.file.exists():
            raise FileNotFoundError(f"Prompt file missing: {spec.file}")
        template = spec.file.read_text(encoding="utf-8")
        vars_full = dict(variables)
        vars_full.setdefault("version", spec.version)

        def repl(match: re.Match) -> str:
            key = match.group(1)
            val = vars_full.get(key, "")
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False, indent=2)
            return "" if val is None else str(val)

        rendered = re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", repl, template)
        return spec, rendered

    @staticmethod
    def input_hash(prompt_version_key: str, rendered: str, schema_name: str = "") -> str:
        blob = f"{prompt_version_key}\n{schema_name}\n{rendered}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
