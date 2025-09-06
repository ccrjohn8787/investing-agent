from __future__ import annotations

from investing_agent.agents.writer import render_report
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.news import NewsItem, NewsSummary


def base_inputs() -> InputsI:
    return InputsI(
        company="NewsCo",
        ticker="NWS",
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        drivers=Drivers(sales_growth=[0.05]*4, oper_margin=[0.15]*4, stable_growth=0.02, stable_margin=0.15),
        sales_to_capital=[2.0]*4,
        wacc=[0.06]*4,
        macro=Macro(risk_free_curve=[0.04]*4, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode="end"),
    )


def base_val() -> ValuationV:
    return ValuationV(pv_explicit=500.0, pv_terminal=1500.0, pv_oper_assets=2000.0, net_debt=0.0, cash_nonop=0.0, equity_value=2000.0, shares_out=1000.0, value_per_share=2.0)


def test_writer_includes_news_section():
    I = base_inputs()
    V = base_val()
    facts = [NewsItem(id="a", title="Guide up", url="u", source="yahoo", published_at="2025-09-01T00:00:00Z", tags=["guidance"]) ]
    impacts = []
    ns = NewsSummary(facts=facts, impacts=impacts)
    md = render_report(I, V, news=ns)
    assert "## News & Impacts" in md
    assert "Guide up" in md
