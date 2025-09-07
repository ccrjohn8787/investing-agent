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


def test_consensus_slope_smoothing():
    I = base_inputs(T=8)
    # Far from stable initially; ensure slope large enough to reach by horizon
    consensus = {
        "growth": [0.12, 0.11],
        "margin": [0.18, 0.175],
        "smooth_to_stable": True,
        "smoothing": {"mode": "slope", "slope_bps_per_year": 200},  # 2% per year
    }
    I2 = consensus_apply(I, consensus_data=consensus)
    # Overrides preserved
    assert I2.drivers.sales_growth[:2] == [0.12, 0.11]
    assert I2.drivers.oper_margin[:2] == [0.18, 0.175]
    # Monotonic approach toward stable; last equals stable (within tol)
    tol = 1e-9
    sg = I2.drivers.stable_growth
    sm = I2.drivers.stable_margin
    # Growth tail monotonic toward sg
    tail_g = I2.drivers.sales_growth[1:]
    for a, b in zip(tail_g, tail_g[1:]):
        # moving downward toward stable
        assert (a >= b) or abs(a - b) < 1e-12
    assert abs(I2.drivers.sales_growth[-1] - sg) < tol
    # Margin tail monotonic toward sm
    tail_m = I2.drivers.oper_margin[1:]
    for a, b in zip(tail_m, tail_m[1:]):
        assert (a >= b) or abs(a - b) < 1e-12
    assert abs(I2.drivers.oper_margin[-1] - sm) < tol


def test_consensus_half_life_smoothing():
    I = base_inputs(T=8)
    consensus = {
        "growth": [0.12, 0.11],
        "margin": [0.18, 0.175],
        "smooth_to_stable": True,
        "smoothing": {"mode": "half_life", "half_life_years": 1.5},
    }
    I2 = consensus_apply(I, consensus_data=consensus)
    # Overrides preserved
    assert I2.drivers.sales_growth[:2] == [0.12, 0.11]
    assert I2.drivers.oper_margin[:2] == [0.18, 0.175]
    # Exponential approach: last element close to stable within tolerance
    sg = I2.drivers.stable_growth
    sm = I2.drivers.stable_margin
    assert abs(I2.drivers.sales_growth[-1] - sg) < 1e-2
    assert abs(I2.drivers.oper_margin[-1] - sm) < 1e-2
