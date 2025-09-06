from __future__ import annotations

import numpy as np

from investing_agent.agents.market import apply as market_apply
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


def base_inputs(T: int = 8, mode: str = "end") -> InputsI:
    return InputsI(
        company="MarketCo",
        ticker="MKT",
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.05] * T,
            oper_margin=[0.15] * T,
            stable_growth=0.02,
            stable_margin=0.15,
        ),
        sales_to_capital=[2.0] * T,
        wacc=[0.06] * T,
        macro=Macro(risk_free_curve=[0.04] * T, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode=mode),
    )


def test_market_solver_moves_toward_target_and_respects_bounds():
    I = base_inputs()
    v0 = kernel_value(I).value_per_share
    target = v0 * 1.20  # aim 20% higher than base
    bounds = {"growth": (0.0, 0.05), "margin": (0.0, 0.03), "s2c": (0.0, 0.5)}
    I2 = market_apply(I, target_value_per_share=target, bounds=bounds, weights={"growth": 1.0, "margin": 1.0, "s2c": 0.5}, steps=(3, 3, 3))
    v1 = kernel_value(I2).value_per_share
    # Should move closer to target and improve value wrt base
    assert v1 > v0
    assert abs(v1 - target) < abs(v0 - target)
    # Bound checks (uniform deltas applied)
    dg = np.array(I2.drivers.sales_growth) - np.array(I.drivers.sales_growth)
    dm = np.array(I2.drivers.oper_margin) - np.array(I.drivers.oper_margin)
    ds = np.array(I2.sales_to_capital) - np.array(I.sales_to_capital)
    assert float(dg.min()) >= bounds["growth"][0] - 1e-9 and float(dg.max()) <= bounds["growth"][1] + 1e-9
    assert float(dm.min()) >= bounds["margin"][0] - 1e-9 and float(dm.max()) <= bounds["margin"][1] + 1e-9
    assert float(ds.min()) >= bounds["s2c"][0] - 1e-9 and float(ds.max()) <= bounds["s2c"][1] + 1e-9

