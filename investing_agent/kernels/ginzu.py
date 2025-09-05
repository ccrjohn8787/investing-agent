from __future__ import annotations

import numpy as np

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def _fcff_path(I: InputsI):
    T = I.horizon()
    rev = np.zeros(T + 1, dtype=float)
    ebit = np.zeros(T, dtype=float)
    fcff = np.zeros(T, dtype=float)
    wacc = np.array(I.wacc, dtype=float)

    rev[0] = float(I.revenue_t0)
    tax_rate = float(I.tax_rate)

    for t in range(T):
        g = float(I.drivers.sales_growth[t])
        m = float(I.drivers.oper_margin[t])
        sigma = float(I.sales_to_capital[t])

        rev[t + 1] = rev[t] * (1.0 + g)
        ebit_t = rev[t + 1] * m

        delta_rev = rev[t + 1] - rev[t]
        reinvest = delta_rev / sigma if sigma > 0 else 0.0

        nopat = ebit_t * (1.0 - tax_rate)
        fcff[t] = nopat - reinvest
        ebit[t] = ebit_t

    return rev[1:], ebit, fcff, wacc


def _discount_factors(wacc: np.ndarray, mode: str) -> np.ndarray:
    T = wacc.shape[0]
    r = wacc
    df = np.ones(T, dtype=float)
    acc = 1.0
    for t in range(T):
        acc *= (1.0 + r[t])
        df[t] = 1.0 / acc
    if mode == "midyear":
        df = df * np.sqrt(1.0 + r)
    return df


def _terminal_value(I: InputsI, rev_T: float):
    g_inf = float(I.drivers.stable_growth)
    m_inf = float(I.drivers.stable_margin)
    r_inf = float(I.wacc[-1])

    if not (g_inf < r_inf - 0.005):
        raise ValueError(
            f"Terminal growth constraint violated: g_inf={g_inf:.4f}, r_inf={r_inf:.4f}"
        )

    rev_T1 = rev_T * (1.0 + g_inf)
    ebit_T1 = rev_T1 * m_inf
    nopat_T1 = ebit_T1 * (1.0 - float(I.tax_rate))

    sigma_T = float(I.sales_to_capital[-1])
    reinvest_T1 = (rev_T1 - rev_T) / sigma_T if sigma_T > 0 else 0.0

    fcff_T1 = nopat_T1 - reinvest_T1
    tv_T = fcff_T1 / (r_inf - g_inf)
    return fcff_T1, tv_T


def value(I: InputsI) -> ValuationV:
    mode = I.discounting.mode
    rev, ebit, fcff, wacc = _fcff_path(I)
    df = _discount_factors(wacc, mode)

    pv_explicit = float((fcff * df).sum())
    _, tv_T = _terminal_value(I, rev[-1])
    pv_terminal = float(tv_T * df[-1])
    pv_oper_assets = pv_explicit + pv_terminal

    equity_value = pv_oper_assets - float(I.net_debt) + float(I.cash_nonop)
    vps = equity_value / float(I.shares_out)

    return ValuationV(
        pv_explicit=pv_explicit,
        pv_terminal=pv_terminal,
        pv_oper_assets=pv_oper_assets,
        net_debt=float(I.net_debt),
        cash_nonop=float(I.cash_nonop),
        equity_value=equity_value,
        shares_out=float(I.shares_out),
        value_per_share=vps,
        notes="end-year" if mode == "end" else "mid-year",
    )

