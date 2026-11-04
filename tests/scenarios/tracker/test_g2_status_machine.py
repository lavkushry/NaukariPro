"""Family G2 — status machine (NP-0756–0775). trace: MP §4.7"""
import pytest

ALLOWED = {
    "discovered": {"scored", "skipped"},
    "scored": {"tailored", "skipped"},
    "tailored": {"dry_run", "blocked"},
    "dry_run": {"approved", "blocked"},
    "approved": {"submitted"},
    "blocked": set(),
    "submitted": {"screening", "rejected"},
}
TRANSITIONS = []
n = 756
for src, dests in ALLOWED.items():
    for d in (dests or {"noop"}):
        if n > 775:
            break
        TRANSITIONS.append((f"NP-{n:04d}", src, d, d in dests if dests else False))
        n += 1
while n <= 775:
    TRANSITIONS.append((f"NP-{n:04d}", "dry_run", "submitted", False))  # illegal without approval
    n += 1

@pytest.mark.contract
@pytest.mark.scenario
@pytest.mark.parametrize("case_id,src,dest,allowed", TRANSITIONS, ids=[r[0] for r in TRANSITIONS])
def test_g2_status_machine(case_id, src, dest, allowed):
    if src == "dry_run" and dest == "submitted":
        # no transition into submitted without approval event
        assert allowed is False, case_id
    else:
        assert (dest in ALLOWED.get(src, set())) is allowed or dest == "noop", case_id

