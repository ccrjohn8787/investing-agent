from __future__ import annotations

from investing_agent.agents.consensus import apply as consensus_apply
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


def base_inputs(T: int = 6) -> InputsI:
    return InputsI(
        company="ConsCo",
        ticker="CNS",
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
        discounting=Discounting(mode="end"),
    )


def test_consensus_maps_first_two_years():
    I = base_inputs()
    consensus = {
        "revenue": [1100.0, 1200.0],  # 10%, then ~9.09%
        "ebit": [170.0, 180.0],       # margins ~15.45%, 15.0%
    }
    I2 = consensus_apply(I, consensus_data=consensus)
    assert abs(I2.drivers.sales_growth[0] - 0.10) < 1e-6
    assert abs(I2.drivers.sales_growth[1] - ((1200.0-1100.0)/1100.0)) < 1e-6
    assert abs(I2.drivers.oper_margin[0] - (170.0/1100.0)) < 1e-6
    assert abs(I2.drivers.oper_margin[1] - (180.0/1200.0)) < 1e-6


def test_consensus_direct_growth_and_margin_arrays():
    I = base_inputs()
    consensus = {
        "growth": [0.12, 0.11, 0.10],
        "margin": [0.18, 0.175, 0.17]
    }
    I2 = consensus_apply(I, consensus_data=consensus)
    assert I2.drivers.sales_growth[:3] == [0.12, 0.11, 0.10]
    assert I2.drivers.oper_margin[:3] == [0.18, 0.175, 0.17]
