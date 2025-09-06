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


def test_market_is_noop_for_now():
    I = base_inputs()
    J = market_apply(I)
    assert J.model_dump() == I.model_dump()


def test_consensus_is_noop_for_now():
    I = base_inputs()
    J = consensus_apply(I)
    assert J.model_dump() == I.model_dump()


def test_comparables_moves_toward_peer_median_with_cap():
    I = base_inputs()
    I.drivers.stable_margin = 0.12
    peers = [{"stable_margin": 0.15}, {"stable_margin": 0.18}, {"stable_margin": 0.14}]  # median=0.15
    policy = {"cap_bps": 100}
    J = comparables_apply(I, peers=peers, policy=policy)
    # Expect move by +0.01 (100 bps) toward 0.15 -> 0.13
    assert abs(J.drivers.stable_margin - 0.13) < 1e-9
