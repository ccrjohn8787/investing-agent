from __future__ import annotations

from investing_agent.schemas.inputs import InputsI, Drivers, Macro, Discounting
from investing_agent.kernels.ginzu import value


def base_inputs(T: int = 10, mode: str = "end") -> InputsI:
    return InputsI(
        company="SyntheticCo",
        ticker="SYN",
        currency="USD",
        shares_out=1_000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.04] * T,
            oper_margin=[0.12] * T,
            stable_growth=0.02,
            stable_margin=0.12,
        ),
        sales_to_capital=[2.0] * T,
        wacc=[0.04] * T,
        macro=Macro(risk_free_curve=[0.04] * T, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode=mode),
    )


def test_pv_bridge_exact():
    I = base_inputs(T=8, mode="end")
    V = value(I)
    assert abs((V.pv_explicit + V.pv_terminal) - V.pv_oper_assets) < 1e-8


def test_midyear_uplift_band():
    I_end = base_inputs(T=12, mode="end")
    I_mid = base_inputs(T=12, mode="midyear")
    V_end = value(I_end)
    V_mid = value(I_mid)
    uplift = (V_mid.pv_oper_assets / V_end.pv_oper_assets) - 1.0
    assert 0.015 <= uplift <= 0.035


def test_gradient_signs():
    I = base_inputs(T=10, mode="end")
    V0 = value(I).equity_value

    I_up_margin = I.model_copy(deep=True)
    I_up_margin.drivers.oper_margin = [m + 0.01 for m in I.drivers.oper_margin]
    V_up_margin = value(I_up_margin).equity_value
    assert V_up_margin > V0

    I_up_wacc = I.model_copy(deep=True)
    I_up_wacc.wacc = [w + 0.01 for w in I.wacc]
    V_up_wacc = value(I_up_wacc).equity_value
    assert V_up_wacc < V0


def test_terminal_constraint_raises():
    I = base_inputs(T=5)
    I.drivers.stable_growth = I.wacc[-1] - 0.003
    try:
        _ = value(I)
        assert False, "Expected ValueError for terminal growth constraint"
    except ValueError:
        pass

