from __future__ import annotations

"""
Market agent (planned)

Applies bounded, schema-checked transforms to InputsI to reconcile structural
assumptions (e.g., WACC path, beta) with market context. No direct LLM math.
"""

from investing_agent.schemas.inputs import InputsI


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def apply(I: InputsI) -> InputsI:
    """
    Bounded, deterministic market reconciliation:
    - Ensure terminal feasibility by nudging WACC path upward (≤ 200 bps per call)
      toward (stable_growth + 100 bps) if violated, clamped to [2%, 20%].
    - Adjust smoothly across the path.
    """
    J = I.model_copy(deep=True)
    T = J.horizon()
    w = list(J.wacc)
    g_inf = float(J.drivers.stable_growth)
    target_min = g_inf + 0.01
    last = float(w[-1])
    if last < target_min:
        # Increase last by at most 200 bps per call
        inc = min(target_min - last, 0.02)
        for t in range(T):
            # Progressive increase towards the end
            factor = (t + 1) / T
            w[t] = _clamp(w[t] + inc * factor, 0.02, 0.20)
        J.wacc = w
    return J
