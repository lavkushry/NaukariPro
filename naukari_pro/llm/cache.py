"""On-disk record/replay cache keyed by (prompt_version, input_hash)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ResponseCache:
    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self.cache_dir = Path(cache_dir) if cache_dir else root / ".llm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, prompt_version: str, input_hash: str) -> Path:
        safe = prompt_version.replace("/", "_").replace("@", "_")
        return self.cache_dir / safe / f"{input_hash}.json"

    def get(self, prompt_version: str, input_hash: str) -> Optional[Dict[str, Any]]:
        path = self._path(prompt_version, input_hash)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, prompt_version: str, input_hash: str, payload: Dict[str, Any]) -> Path:
        path = self._path(prompt_version, input_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
