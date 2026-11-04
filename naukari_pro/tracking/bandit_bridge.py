"""Outcome labels → LinUCB reward updates."""

from __future__ import annotations

from typing import Any, Dict, Optional


REWARD_MAP = {
    "offer": 1.0,
    "interview": 0.7,
    "screening": 0.4,
    "applied": 0.1,
    "rejected": -0.5,
    "ghosted": -0.3,
    "duplicate": -2.0,
}


def reward_for_status(status: str) -> float:
    return float(REWARD_MAP.get((status or "").lower(), 0.0))


def update_bandit_from_outcome(
    job_context: Dict[str, Any],
    status: str,
    *,
    action: str = "APPLY",
    policy: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Feed reward into existing LinUCB policy when available.
    Returns {reward, updated, error}.
    """
    reward = reward_for_status(status)
    if policy is None:
        try:
            from naukari_pro.modules.learning.policy import LinUCBBanditPolicy, PolicyAction, extract_context_vector
            policy = LinUCBBanditPolicy()
            # try load persisted state if method exists
            if hasattr(policy, "load"):
                try:
                    policy.load()
                except Exception:
                    pass
        except Exception as exc:  # noqa: BLE001
            return {"reward": reward, "updated": False, "error": str(exc)}

    try:
        from naukari_pro.modules.learning.policy import PolicyAction, extract_context_vector

        x = extract_context_vector(job_context)
        act = PolicyAction.APPLY
        if hasattr(PolicyAction, action):
            act = getattr(PolicyAction, action)
        elif action.upper() == "SKIP":
            act = PolicyAction.SKIP
        elif action.upper() in ("DEFER_TO_REVIEW", "REVIEW"):
            act = PolicyAction.DEFER_TO_REVIEW

        if hasattr(policy, "update"):
            policy.update(x, act, reward)
        elif hasattr(policy, "observe"):
            policy.observe(x, act, reward)
        else:
            return {"reward": reward, "updated": False, "error": "policy has no update method"}

        if hasattr(policy, "save"):
            try:
                policy.save()
            except Exception:
                pass
        return {"reward": reward, "updated": True, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"reward": reward, "updated": False, "error": str(exc)}
