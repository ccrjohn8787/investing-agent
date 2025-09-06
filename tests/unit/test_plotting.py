from __future__ import annotations

from datetime import date

from investing_agent.agents.plotting import plot_price_vs_value, plot_pv_bridge
from investing_agent.schemas.prices import PriceSeries, PriceBar
from investing_agent.schemas.valuation import ValuationV


def test_plot_price_vs_value_bytes():
    ps = PriceSeries(
        ticker="T",
        bars=[
            PriceBar(date=date(2024, 1, 1), open=10, high=11, low=9, close=10.5),
            PriceBar(date=date(2024, 1, 2), open=10.6, high=11, low=10.2, close=10.8),
        ],
    )
    b = plot_price_vs_value(ps, value_per_share=11.0)
    assert isinstance(b, (bytes, bytearray)) and len(b) > 0


def test_plot_pv_bridge_bytes():
    V = ValuationV(
        pv_explicit=100.0,
        pv_terminal=300.0,
        pv_oper_assets=400.0,
        net_debt=50.0,
        cash_nonop=20.0,
        equity_value=370.0,
        shares_out=100.0,
        value_per_share=3.7,
    )
    b = plot_pv_bridge(V)
    assert isinstance(b, (bytes, bytearray)) and len(b) > 0

