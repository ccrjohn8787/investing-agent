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
) -> InputsI:
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

    # Smooth paths to stable
    sales_growth = list(np.linspace(g0, stable_growth, horizon))
    oper_margin = list(np.linspace(m0, stable_margin, horizon))

    # Sales to capital: default 2.0 trending to 2.5
    sales_to_capital = list(np.linspace(2.0, 2.5, horizon))

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
