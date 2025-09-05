from __future__ import annotations

import numpy as np

from investing_agent.agents.sensitivity import compute_sensitivity
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


def base_inputs(T: int = 8, mode: str = "end") -> InputsI:
    return InputsI(
        company="SyntheticCo",
        ticker="SYN",
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


def test_sensitivity_monotonicity():
    I = base_inputs()
    res = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(3, 3))
    # Higher growth and margin should increase value wrt base (heuristic check corners)
    base = res.base_value_per_share
    low_low = res.grid[0, 0]
    high_high = res.grid[-1, -1]
    assert low_low <= base <= high_high

