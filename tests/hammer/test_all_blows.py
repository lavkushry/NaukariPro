"""Big Hammer Protocol — all 420 blows parametrized (distinct catalog vectors)."""

from __future__ import annotations

import pytest

from tests.hammer.attacks import ATTACKS
from tests.hammer.blow_registry import ALL_BLOWS
from tests.hammer.harness import check_basic_invariants, run_blow


@pytest.mark.hammer
@pytest.mark.parametrize(
    "blow",
    ALL_BLOWS,
    ids=[b["blow_id"] for b in ALL_BLOWS],
)
def test_hammer_blow(blow: dict) -> None:
    attack_name = blow["attack"]
    attack = ATTACKS.get(attack_name)
    assert attack is not None, f"missing attack for {attack_name}"
    expect = blow.get("expect") or "contained"
    result = run_blow(
        blow_id=blow["blow_id"],
        hammer=blow["hammer"],
        vector=blow["vector"],
        target=blow["target"],
        attack=attack,
        expect=expect,
    )
    assert result.outcome != "broke_unfixed"
    if expect == "contained":
        assert result.outcome == "contained", (
            f"{blow['blow_id']} expected contained refuse, got {result.outcome}: {result.observed}"
        )
    else:
        assert result.outcome in ("survived", "contained", "broke_fixed")
    violations = check_basic_invariants()
    assert not violations, violations
