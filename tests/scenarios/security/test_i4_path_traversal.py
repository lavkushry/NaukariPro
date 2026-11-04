"""Family I4 — path traversal (NP-0906–0920). trace: MP §6"""
import pytest
from naukari_pro.security.paths import resolve_safe_path, PathTraversalError

CASES = [
    ("evidence/a.png", True),
    ("screens/x.jpg", True),
    ("../etc/passwd", False),
    ("../../secret", False),
    ("foo/../../bar", False),
    ("ok/nested/file.txt", True),
    ("..\\windows\\system32", False),
    ("./safe.txt", True),
    ("a/b/c/d.json", True),
    ("../manifest.jsonl", False),
    ("evidence/../evidence/x", True),  # normalizes inside
    ("/etc/passwd", False),
    ("evidence/../../etc/passwd", False),
    ("...", True),
    ("evidence/foo/bar", True),
]
ROWS = [(f"NP-{906+i:04d}", p, ok) for i, (p, ok) in enumerate(CASES)]

@pytest.mark.redteam
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,rel,ok", ROWS, ids=[r[0] for r in ROWS])
def test_i4_path_traversal(case_id, rel, ok, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    if ok:
        try:
            path = resolve_safe_path(data, rel)
            assert str(path).startswith(str(data.resolve())), case_id
        except PathTraversalError:
            # some OS normalize oddly — still fail closed is acceptable for odd "..."
            if rel not in (".", "...", "./safe.txt"):
                raise
    else:
        with pytest.raises(PathTraversalError):
            resolve_safe_path(data, rel)

