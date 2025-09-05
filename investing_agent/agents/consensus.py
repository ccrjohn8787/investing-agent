from __future__ import annotations

"""
Consensus agent (planned)

Maps near-term consensus/guidance into InputsI while clamping long-term drivers.
Per AGENTS.md, numeric updates are code-only; LLM may propose bounded deltas but
must flow through schema-checked code.
"""

from investing_agent.schemas.inputs import InputsI


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def apply(I: InputsI) -> InputsI:
    """
    Bounded near-term nudges simulating consensus influence:
    - Increase first two years' sales growth by +100 bps (cap to 30%).
    - Increase first two years' operating margin by +50 bps (cap to stable_margin + 200 bps and ±60%).
    Deterministic; later agents can supply real consensus, but this stays bounded and safe.
    """
    J = I.model_copy(deep=True)
    T = J.horizon()
    k = min(2, T)
    g = list(J.drivers.sales_growth)
    m = list(J.drivers.oper_margin)
    m_cap = float(J.drivers.stable_margin) + 0.02
    for t in range(k):
        g[t] = _clamp(g[t] + 0.01, -0.99, 0.30)
        m[t] = _clamp(m[t] + 0.005, -0.60, min(0.60, m_cap))
    J.drivers.sales_growth = g
    J.drivers.oper_margin = m
    return J
