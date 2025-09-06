from __future__ import annotations

"""
Comparables agent (planned)

Selects a peer set and runs relative diagnostics. Applies only bounded, defensible
updates to InputsI (e.g., convergence of stable margin toward peer median within
limits). No LLM math.
"""

from investing_agent.schemas.inputs import InputsI


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def apply(I: InputsI, peers: list[dict] | None = None, policy: dict | None = None) -> InputsI:
    """
    Comparables agent — minimal eval-driven implementation.

    Behavior (to satisfy current eval):
    - If peers provided with 'stable_margin', compute their median.
    - Move current stable_margin toward the median by at most `cap_bps` (default 100 bps).
    - Clamp resulting stable_margin to [5%, 35%].
    - Does not alter the yearly margin path (future work can nudge tail margins with policy).
    """
    J = I.model_copy(deep=True)
    if not peers:
        return J
    try:
        sm_peers = [float(p["stable_margin"]) for p in peers if "stable_margin" in p]
    except Exception:
        return J
    if not sm_peers:
        return J
    sm_peers_sorted = sorted(sm_peers)
    med = sm_peers_sorted[len(sm_peers_sorted) // 2]
    cap_bps = float((policy or {}).get("cap_bps", 100))
    cap = cap_bps / 10000.0
    sm0 = float(J.drivers.stable_margin)
    gap = med - sm0
    delta = max(-cap, min(cap, gap))
    J.drivers.stable_margin = _clamp(sm0 + delta, 0.05, 0.35)
    return J
