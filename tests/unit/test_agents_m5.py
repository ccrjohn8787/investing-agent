from __future__ import annotations

from investing_agent.agents.market import apply as market_apply
from investing_agent.agents.consensus import apply as consensus_apply
from investing_agent.agents.comparables import apply as comparables_apply
from investing_agent.schemas.inputs import InputsI, Drivers, Macro, Discounting


def base_inputs(T: int = 6) -> InputsI:
    return InputsI(
        company="M5Co",
        ticker="M5",
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.05] * T,
            oper_margin=[0.12] * T,
            stable_growth=0.02,
            stable_margin=0.12,
        ),
        sales_to_capital=[2.0] * T,
        wacc=[0.03] * T,
        macro=Macro(risk_free_curve=[0.03] * T, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode="end"),
    )


def test_market_nudges_wacc_up_bounded():
    I = base_inputs()
    # make terminal constraint tighter
    I.drivers.stable_growth = 0.06
    I.wacc = [0.05] * I.horizon()
    J = market_apply(I)
    assert J.wacc[-1] >= I.wacc[-1]
    assert J.wacc[-1] <= I.wacc[-1] + 0.0200001
    assert min(J.wacc) >= 0.02 and max(J.wacc) <= 0.20


def test_consensus_nudges_front_years():
    I = base_inputs()
    J = consensus_apply(I)
    assert J.drivers.sales_growth[0] > I.drivers.sales_growth[0]
    assert J.drivers.oper_margin[0] > I.drivers.oper_margin[0]
    # bounded
    assert J.drivers.sales_growth[0] <= 0.30
    assert J.drivers.oper_margin[0] <= I.drivers.stable_margin + 0.02


def test_comparables_moves_stable_margin_toward_median():
    I = base_inputs()
    # Make median margin substantially higher
    I.drivers.oper_margin = [0.20] * I.horizon()
    I.drivers.stable_margin = 0.10
    J = comparables_apply(I)
    assert J.drivers.stable_margin > I.drivers.stable_margin
    # tail margins nudged toward stable
    assert J.drivers.oper_margin[-1] != I.drivers.oper_margin[-1]

