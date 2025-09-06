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


def apply(I: InputsI, consensus_data: dict | None = None) -> InputsI:
    """
    Consensus agent (contract stub — eval-first).

    Purpose (per paper):
    - Obtain analyst consensus/guidance and map to near-term spreadsheet drivers
      (first N years), while clamping long-term drivers to stable targets.

    Contract (target state):
    - Inputs: `InputsI`, optional `consensus_data` schema with vendor fields.
    - Output: new `InputsI` with near-term overrides; numeric mapping done in code; bounds enforced.
    - Determinism: fully deterministic given consensus input.
    - Provenance: cite consensus snapshots; record mapping and clamps.

    Behavior:
    - If `consensus_data` is None or missing required fields, returns a deep copy (no-op).
    - Otherwise maps the first two years as:
        g1 = (rev1 - rev0) / rev0; g2 = (rev2 - rev1) / rev1
        m1 = ebit1 / rev1;       m2 = ebit2 / rev2
      and writes them into the first two positions of the sales_growth and oper_margin paths
      (when horizon >= 2). Values are clamped to reasonable bounds.
    - Remaining years unchanged; long-term clamping policies to be added with real connectors.
    """
    J = I.model_copy(deep=True)
    if not consensus_data:
        return J
    try:
        rev = list(consensus_data.get("revenue", []))
        ebit = list(consensus_data.get("ebit", []))
    except Exception:
        return J
    if len(rev) < 2 or len(ebit) < 2:
        return J
    # Base revenue at t0 inferred from InputsI.revenue_t0
    rev0 = float(J.revenue_t0)
    rev1 = float(rev[0])
    rev2 = float(rev[1])
    ebit1 = float(ebit[0])
    ebit2 = float(ebit[1])

    g_path = list(J.drivers.sales_growth)
    m_path = list(J.drivers.oper_margin)
    if len(g_path) >= 1 and rev0 > 0:
        g1 = (rev1 - rev0) / rev0
        g_path[0] = _clamp(g1, -0.99, 0.60)
    if len(g_path) >= 2 and rev1 > 0:
        g2 = (rev2 - rev1) / rev1
        g_path[1] = _clamp(g2, -0.99, 0.60)
    if len(m_path) >= 1 and rev1 > 0:
        m1 = ebit1 / rev1
        m_path[0] = _clamp(m1, -0.60, 0.60)
    if len(m_path) >= 2 and rev2 > 0:
        m2 = ebit2 / rev2
        m_path[1] = _clamp(m2, -0.60, 0.60)
    J.drivers.sales_growth = g_path
    J.drivers.oper_margin = m_path
    return J
