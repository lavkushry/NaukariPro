"""Path containment — evidence/file writes must stay under project data dir."""

from __future__ import annotations

from pathlib import Path


class PathTraversalError(ValueError):
    pass


def resolve_safe_path(data_dir: Path, user_path: str) -> Path:
    root = Path(data_dir).resolve()
    candidate = (root / user_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PathTraversalError(f"path escapes data dir: {user_path}") from exc
    return candidate


def assert_within_data_dir(data_dir: Path, user_path: str) -> Path:
    return resolve_safe_path(data_dir, user_path)
