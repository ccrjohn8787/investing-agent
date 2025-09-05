from __future__ import annotations

from typing import List, Optional

import numpy as np

from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


def _cagr(series: List[float]) -> float:
    if len(series) < 2:
        return 0.03
    s0, sN = float(series[0]), float(series[-1])
    n = len(series) - 1
    if s0 <= 0 or sN <= 0:
        return 0.02
    return (sN / s0) ** (1 / n) - 1


def build_inputs_from_fundamentals(
    f: Fundamentals,
    horizon: int = 10,
    stable_growth: Optional[float] = None,
    stable_margin: Optional[float] = None,
    beta: float = 1.0,
    macro: Optional[Macro] = None,
    discounting: Optional[Discounting] = None,
    # Optional user-provided paths to explicitly express views.
    # If provided with length < horizon, the remainder will be smoothly trended
    # to the stable target. If provided with length == horizon, it is used as-is.
    sales_growth_path: Optional[List[float]] = None,
    oper_margin_path: Optional[List[float]] = None,
    sales_to_capital_path: Optional[List[float]] = None,
) -> InputsI:
    """
    Build kernel inputs from fundamentals, with optional explicit overrides for
    growth, margin, and sales-to-capital paths so users can express judgement.

    Path override rules:
    - If an override list has len == horizon, it is used verbatim.
    - If len < horizon, the prefix is used and the remaining years are
      linearly trended from the last provided value to the respective stable
      target (growth->stable_growth, margin->stable_margin, s2c->2.5 default).
    - If an override is None or empty, a default smooth path is constructed
      from historical estimates to the stable target.
    """
    years = sorted(f.revenue.keys())
    rev_series = [f.revenue[y] for y in years]
    ebit_series = [f.ebit.get(y, 0.0) for y in years]
    margin_hist = [0.0 if r == 0 else e / r for r, e in zip(rev_series, ebit_series)]

    g0 = max(-0.2, min(0.25, _cagr(rev_series[-min(5, len(rev_series)): ])))
    # Prefer TTM margin when available
    if f.revenue_ttm and f.ebit_ttm and f.revenue_ttm > 0:
        m0 = float(f.ebit_ttm) / float(f.revenue_ttm)
    else:
        m0 = float(margin_hist[-1]) if margin_hist else 0.1

    if stable_growth is None:
        # conservative: min(2.5%, last rf)
        rf_guess = (macro.risk_free_curve[-1] if macro and macro.risk_free_curve else 0.025)
        stable_growth = min(0.03, max(0.0, rf_guess))
    if stable_margin is None:
        stable_margin = max(0.05, min(0.35, m0))

    # Helper to merge optional override with smooth trend to a target
    def _merge_path(prefix: Optional[List[float]], start: float, target: float, n: int) -> List[float]:
        if prefix is None or len(prefix) == 0:
            return list(np.linspace(start, target, n))
        if len(prefix) >= n:
            return list(prefix[:n])
        k = len(prefix)
        tail = list(np.linspace(prefix[-1], target, n - k))
        return list(prefix + tail)

    # Smooth/default paths to stable, then apply overrides
    default_sales_growth = list(np.linspace(g0, stable_growth, horizon))
    default_oper_margin = list(np.linspace(m0, stable_margin, horizon))
    default_s2c = list(np.linspace(2.0, 2.5, horizon))

    sales_growth = _merge_path(sales_growth_path, g0, float(stable_growth), horizon)
    oper_margin = _merge_path(oper_margin_path, m0, float(stable_margin), horizon)
    sales_to_capital = _merge_path(sales_to_capital_path, 2.0, 2.5, horizon)

    # If no overrides were provided at all, keep deterministic defaults
    if sales_growth_path is None:
        sales_growth = default_sales_growth
    if oper_margin_path is None:
        oper_margin = default_oper_margin
    if sales_to_capital_path is None:
        sales_to_capital = default_s2c

    # WACC path from macro: rf + ERP * beta; no leverage adj yet
    if macro is None:
        macro = Macro(risk_free_curve=[0.03] * horizon, erp=0.05, country_risk=0.0)
    rf_curve = macro.risk_free_curve or [0.03] * horizon
    rf_curve = (rf_curve + [rf_curve[-1]] * horizon)[:horizon]
    wacc = [max(0.02, min(0.20, rf_curve[t] + (macro.erp + macro.country_risk) * beta)) for t in range(horizon)]

    disc = discounting or Discounting(mode="end")

    I = InputsI(
        company=f.company,
        ticker=f.ticker,
        currency=f.currency,
        asof_date=f.asof_date,
        shares_out=float(f.shares_out or 1.0),
        tax_rate=float(f.tax_rate or 0.25),
        revenue_t0=float(f.revenue_ttm if (f.revenue_ttm and f.revenue_ttm > 0) else (rev_series[-1] if rev_series else 0.0)),
        net_debt=float(f.net_debt or 0.0),
        cash_nonop=float(f.cash_nonop or 0.0),
        drivers=Drivers(
            sales_growth=sales_growth,
            oper_margin=oper_margin,
            stable_growth=float(stable_growth),
            stable_margin=float(stable_margin),
        ),
        sales_to_capital=sales_to_capital,
        wacc=wacc,
        macro=macro,
        discounting=disc,
    )

    # Sanity bounds
    _ = I.horizon()  # validate path length equality
    return I
