"""JSON Schema validation layer — every LLM response must pass before use."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ValidationError(ValueError):
    pass


def _type_ok(value: Any, expected: str) -> bool:
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    py = mapping.get(expected)
    if py is None:
        return True
    return isinstance(value, py)


def _validate(instance: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    errors: List[str] = []
    if "type" in schema:
        types = schema["type"]
        type_list = types if isinstance(types, list) else [types]
        if not any(_type_ok(instance, t) for t in type_list):
            errors.append(f"{path}: expected {types}, got {type(instance).__name__}")
            return errors

    if schema.get("type") == "object" or "properties" in schema:
        if not isinstance(instance, dict):
            return errors
        for req in schema.get("required") or []:
            if req not in instance:
                errors.append(f"{path}: missing required '{req}'")
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            for k in instance:
                if k not in props:
                    errors.append(f"{path}: unexpected property '{k}'")
        for k, sub in props.items():
            if k in instance:
                errors.extend(_validate(instance[k], sub, f"{path}.{k}"))

    if schema.get("type") == "array" or "items" in schema:
        if isinstance(instance, list) and "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(_validate(item, schema["items"], f"{path}[{i}]"))

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum")
    if "minimum" in schema and isinstance(instance, (int, float)) and instance < schema["minimum"]:
        errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
    if "maximum" in schema and isinstance(instance, (int, float)) and instance > schema["maximum"]:
        errors.append(f"{path}: {instance} > maximum {schema['maximum']}")
    if "maxLength" in schema and isinstance(instance, str) and len(instance) > schema["maxLength"]:
        errors.append(f"{path}: string longer than {schema['maxLength']}")
    return errors


def load_schema(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_response(data: Any, schema: Optional[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    if schema is None:
        return True, []
    errs = _validate(data, schema)
    return (len(errs) == 0), errs


def parse_json_content(text: str) -> Any:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)
