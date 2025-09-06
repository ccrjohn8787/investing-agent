from __future__ import annotations

"""
Market agent (planned)

Applies bounded, schema-checked transforms to InputsI to reconcile structural
assumptions (e.g., WACC path, beta) with market context. No direct LLM math.
"""

from investing_agent.schemas.inputs import InputsI
from investing_agent.kernels.ginzu import value as kernel_value


def apply(I: InputsI, context: dict | None = None) -> InputsI:
    """
    Market reconciliation agent (contract stub — eval-first).

    Purpose (per paper):
    - When asked to reconcile intrinsic value to market price, find the smallest
      bounded changes to the value drivers that match the observed market price,
      with a transparent rationale and provenance.

    Contract (target state):
    - Inputs: `InputsI`, optional `context` with
      {"target_price", "weights", "bounds", "penalties"}.
    - Output: new `InputsI` with proposed deltas; numeric changes derive from a
      code solver (least-squares with bounds), never from an LLM.
    - Determinism: fully deterministic given inputs and bounds.
    - Provenance: record rationale and constraints in event log; cite snapshots.

    Solver (current minimal implementation):
    - Adjust only the stable margin toward the target price using bounded bisection
      within ±cap_bps (default 100 bps), clamped to [5%, 35%].
    - If no target provided, return no-op copy.
    """
    J = I.model_copy(deep=True)
    if not context or "target_price" not in context:
        return J
    target = float(context.get("target_price"))
    cap_bps = float(context.get("cap_bps", 100.0))
    cap = cap_bps / 10000.0
    sm0 = float(J.drivers.stable_margin)
    lo = max(0.05, sm0 - cap)
    hi = min(0.35, sm0 + cap)

    def vps(sm: float) -> float:
        K = J.model_copy(deep=True)
        K.drivers.stable_margin = float(sm)
        return kernel_value(K).value_per_share

    vl = vps(lo)
    vh = vps(hi)
    # If target outside bracket, choose closest bound
    if target <= min(vl, vh) or target >= max(vl, vh):
        chosen = lo if abs(vl - target) <= abs(vh - target) else hi
        J.drivers.stable_margin = chosen
        return J

    # Ensure monotonic direction for bisection: if vl > vh, swap and track
    a, fa = lo, vl
    b, fb = hi, vh
    if fa > fb:
        a, b = b, a
        fa, fb = fb, fa
    # Now fa <= fb; target between fa and fb
    for _ in range(20):
        m = 0.5 * (a + b)
        fm = vps(m)
        if fm < target:
            a, fa = m, fm
        else:
            b, fb = m, fm
    J.drivers.stable_margin = 0.5 * (a + b)
    return J
