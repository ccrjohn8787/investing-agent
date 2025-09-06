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
        growth = list(consensus_data.get("growth", []))
        margin = list(consensus_data.get("margin", []))
    except Exception:
        return J

    g_path = list(J.drivers.sales_growth)
    m_path = list(J.drivers.oper_margin)
    T = len(g_path)

    # Option A: direct growth/margin arrays provided
    last_g_idx = -1
    last_m_idx = -1
    if growth:
        for i in range(min(T, len(growth))):
            try:
                g_path[i] = _clamp(float(growth[i]), -0.99, 0.60)
                last_g_idx = max(last_g_idx, i)
            except Exception:
                continue
    if margin:
        for i in range(min(T, len(margin))):
            try:
                m_path[i] = _clamp(float(margin[i]), -0.60, 0.60)
                last_m_idx = max(last_m_idx, i)
            except Exception:
                continue

    # Option B: map from revenue/ebit arrays if available
    if rev and ebit:
        rev0 = float(J.revenue_t0)
        prev = rev0
        for i in range(min(T, len(rev))):
            try:
                r = float(rev[i])
                e = float(ebit[i])
            except Exception:
                continue
            if prev and i < len(g_path):
                g = (r - prev) / prev if prev else 0.0
                g_path[i] = _clamp(g, -0.99, 0.60)
                last_g_idx = max(last_g_idx, i)
            if r and i < len(m_path):
                m = e / r if r else 0.0
                m_path[i] = _clamp(m, -0.60, 0.60)
                last_m_idx = max(last_m_idx, i)
            prev = r

    # Gentle smoothing: trend tail back to stable values over remaining horizon
    smooth = bool(consensus_data.get("smooth_to_stable", True)) if consensus_data else True
    if smooth and T > 0:
        # Growth toward stable_growth
        sg = float(J.drivers.stable_growth)
        start_idx = last_g_idx + 1
        if start_idx < T and last_g_idx >= 0:
            g_last = float(g_path[last_g_idx])
            span = max(1, T - start_idx)
            for i in range(start_idx, T):
                alpha = (i - start_idx + 1) / float(span)
                g_path[i] = _clamp((1 - alpha) * g_last + alpha * sg, -0.99, 0.60)
        # Margin toward stable_margin
        sm = float(J.drivers.stable_margin)
        start_idx_m = last_m_idx + 1
        if start_idx_m < T and last_m_idx >= 0:
            m_last = float(m_path[last_m_idx])
            span_m = max(1, T - start_idx_m)
            for i in range(start_idx_m, T):
                alpha = (i - start_idx_m + 1) / float(span_m)
                m_path[i] = _clamp((1 - alpha) * m_last + alpha * sm, -0.60, 0.60)

    J.drivers.sales_growth = g_path
    J.drivers.oper_margin = m_path
    return J
