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


def _smooth_tail(
    path: list[float],
    start_idx: int,
    stable: float,
    *,
    mode: str = "slope",
    slope: float = 0.005,
    half_life_years: float = 2.0,
    bounds: tuple[float, float] = (-1.0, 1.0),
) -> list[float]:
    """Smooth path[start_idx:] toward stable value.

    Modes:
    - slope: move toward stable by at most `slope` per year; schedule ensures last element reaches stable
      if horizon allows (never overshoots; monotonic toward target).
    - half_life: exponential approach with factor k = 1 - 0.5**(1/half_life_years).
    - linear_span: internal mode used to preserve legacy behavior (linear interpolation to stable by T-1).
    Bounds are enforced at each step.
    """
    T = len(path)
    if start_idx <= 0 or start_idx >= T:
        return path
    lo, hi = bounds

    # Ensure previous value exists as the base for smoothing
    prev = float(path[start_idx - 1])
    target = float(stable)

    if mode == "linear_span":
        span = max(1, T - start_idx)
        for i in range(start_idx, T):
            alpha = (i - start_idx + 1) / float(span)
            v = (1.0 - alpha) * prev + alpha * target
            path[i] = _clamp(v, lo, hi)
        return path

    if mode == "half_life":
        # Compute per-step approach factor
        try:
            k = 1.0 - (0.5 ** (1.0 / float(half_life_years)))
        except Exception:
            k = 1.0 - (0.5 ** 0.5)
        for i in range(start_idx, T):
            v_prev = float(path[i - 1]) if i > 0 else prev
            v = v_prev + (target - v_prev) * k
            path[i] = _clamp(v, lo, hi)
        return path

    # Default: slope mode
    s = abs(float(slope))
    # We schedule steps so that the last element equals target without exceeding slope per step.
    for i in range(start_idx, T):
        v_prev = float(path[i - 1]) if i > 0 else prev
        gap = target - v_prev
        remaining_steps = (T - 1) - i  # steps after this one
        # Minimum step needed now so that we can still finish within remaining steps at <= s each
        min_needed = max(0.0, abs(gap) - s * max(0, remaining_steps))
        step = min(s, max(0.0, min_needed))
        v = v_prev + (step if gap >= 0 else -step)
        # Do not overshoot target due to rounding
        if (gap >= 0 and v > target) or (gap < 0 and v < target):
            v = target
        path[i] = _clamp(v, lo, hi)
    return path


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

    # Smoothing: trend tail back to stable values over remaining horizon
    smooth = bool(consensus_data.get("smooth_to_stable", True)) if consensus_data else True
    if smooth and T > 0:
        # Extract smoothing config
        smoothing_cfg = (consensus_data or {}).get("smoothing") or {}
        # Back-compat: if no explicit smoothing config provided, use legacy linear behavior
        has_explicit_cfg = bool(smoothing_cfg)
        mode = str(smoothing_cfg.get("mode", "slope" if has_explicit_cfg else "linear_span")).lower()
        slope_bps = float(smoothing_cfg.get("slope_bps_per_year", 50.0))
        slope = slope_bps / 10000.0
        half_life_years = float(smoothing_cfg.get("half_life_years", 2.0))
        # Bounds (optional overrides)
        bcfg = (consensus_data or {}).get("bounds") or {}
        g_bounds = tuple(bcfg.get("growth", [-0.99, 0.60]))  # type: ignore
        m_bounds = tuple(bcfg.get("margin", [-0.60, 0.60]))  # type: ignore

        # Growth toward stable_growth
        sg = float(J.drivers.stable_growth)
        start_idx_g = last_g_idx + 1
        if start_idx_g < T and last_g_idx >= 0:
            g_path = _smooth_tail(
                g_path,
                start_idx_g,
                sg,
                mode=mode,
                slope=slope,
                half_life_years=half_life_years,
                bounds=(float(g_bounds[0]), float(g_bounds[1])),
            )
        # Margin toward stable_margin
        sm = float(J.drivers.stable_margin)
        start_idx_m = last_m_idx + 1
        if start_idx_m < T and last_m_idx >= 0:
            m_path = _smooth_tail(
                m_path,
                start_idx_m,
                sm,
                mode=mode,
                slope=slope,
                half_life_years=half_life_years,
                bounds=(float(m_bounds[0]), float(m_bounds[1])),
            )

    J.drivers.sales_growth = g_path
    J.drivers.oper_margin = m_path
    return J
