from __future__ import annotations

"""
Comparables agent (planned)

Selects a peer set and runs relative diagnostics. Applies only bounded, defensible
updates to InputsI (e.g., convergence of stable margin toward peer median within
limits). No LLM math.
"""

from statistics import median

from investing_agent.schemas.inputs import InputsI


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def apply(I: InputsI) -> InputsI:
    """
    Bounded, defensible relative adjustment:
    - Move stable margin toward the median of the current margin path by up to 200 bps.
    - Nudge the last three years of the margin path 50% toward the (possibly adjusted) stable margin.
    - Clamp stable margin to [5%, 35%] and margins to ±60%.
    """
    J = I.model_copy(deep=True)
    T = J.horizon()
    m = list(J.drivers.oper_margin)
    if not m:
        return J
    med = float(median(m))
    sm = float(J.drivers.stable_margin)
    gap = med - sm
    if abs(gap) > 1e-12:
        delta = _clamp(gap * 0.5, -0.02, 0.02)  # ≤ 200 bps
        sm_new = _clamp(sm + delta, 0.05, 0.35)
        J.drivers.stable_margin = sm_new
    else:
        sm_new = sm
    # Nudge tail margins toward stable
    for t in range(max(0, T - 3), T):
        m[t] = _clamp(m[t] + 0.5 * (sm_new - m[t]), -0.60, 0.60)
    J.drivers.oper_margin = m
    return J
