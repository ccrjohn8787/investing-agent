from __future__ import annotations

from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value
from investing_agent.schemas.fundamentals import Fundamentals


def test_overrides_trend_and_verbatim():
    f = Fundamentals(
        company="X",
        ticker="X",
        currency="USD",
        revenue={2021: 900, 2022: 1000, 2023: 1100},
        ebit={2021: 90, 2022: 110, 2023: 121},
        shares_out=100.0,
        tax_rate=0.25,
    )

    # Prefix override shorter than horizon trends to stable
    I = build_inputs_from_fundamentals(
        f,
        horizon=6,
        stable_growth=0.03,
        stable_margin=0.15,
        sales_growth_path=[0.08, 0.07],
        oper_margin_path=[0.20, 0.19],
        sales_to_capital_path=[2.0, 2.2],
    )
    assert I.drivers.sales_growth[:2] == [0.08, 0.07]
    assert abs(I.drivers.sales_growth[-1] - 0.03) < 1e-9
    assert I.drivers.oper_margin[:2] == [0.20, 0.19]
    assert abs(I.drivers.oper_margin[-1] - 0.15) < 1e-9
    assert I.sales_to_capital[:2] == [2.0, 2.2]
    assert abs(I.sales_to_capital[-1] - 2.5) < 1e-9

    # Verbatim override equal to horizon
    I2 = build_inputs_from_fundamentals(
        f,
        horizon=3,
        stable_growth=0.03,
        stable_margin=0.15,
        sales_growth_path=[0.10, 0.09, 0.08],
        oper_margin_path=[0.18, 0.18, 0.18],
        sales_to_capital_path=[2.1, 2.1, 2.1],
    )
    assert I2.drivers.sales_growth == [0.10, 0.09, 0.08]
    assert I2.drivers.oper_margin == [0.18, 0.18, 0.18]
    assert I2.sales_to_capital == [2.1, 2.1, 2.1]


def test_writer_includes_per_year_and_fundamentals_section():
    f = Fundamentals(
        company="Syn",
        ticker="SYN",
        currency="USD",
        revenue={2022: 800, 2023: 1000},
        ebit={2022: 80, 2023: 110},
        shares_out=1000.0,
        tax_rate=0.25,
    )
    I = build_inputs_from_fundamentals(f, horizon=4, stable_growth=0.02, stable_margin=0.12)
    V = value(I)
    md = render_report(I, V, fundamentals=f)
    assert "## Per-Year Detail" in md
    assert "| Year | Revenue |" in md
    assert "## Fundamentals (Parsed)" in md
    assert "| 2023 |" in md

