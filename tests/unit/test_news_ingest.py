from __future__ import annotations

from investing_agent.agents.news import ingest_and_update, heuristic_summarize
from investing_agent.schemas.news import NewsBundle, NewsItem
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro
from investing_agent.kernels.ginzu import value as kernel_value


def base_inputs(T: int = 6) -> InputsI:
    return InputsI(
        company="NewsCo",
        ticker="NWS",
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


def test_news_ingest_applies_bounded_impacts():
    I = base_inputs()
    V = kernel_value(I)
    # Build a dummy bundle with guidance and tariff tags through heuristic
    items = [
        NewsItem(id="a", title="Company raises guidance for FY", url="u1", source="s", published_at="2025-09-01T00:00:00Z"),
        NewsItem(id="b", title="Tariff risk from new regulations", url="u2", source="s", published_at="2025-09-02T00:00:00Z"),
    ]
    bundle = NewsBundle(ticker="NWS", asof="2025-09-03T00:00:00Z", items=items)
    summary = heuristic_summarize(bundle, I, scenario={"news_caps": {"growth_bps": 50, "margin_bps": 30}})
    I2 = ingest_and_update(I, V, summary, scenario={"news_caps": {"growth_bps": 50, "margin_bps": 30}})
    # Growth should be nudged up in year 1; margin down year 1 within caps
    assert I2.drivers.sales_growth[0] > I.drivers.sales_growth[0]
    assert I2.drivers.oper_margin[0] < I.drivers.oper_margin[0]
    # No out-of-bounds
    assert all(-0.99 <= g <= 0.60 for g in I2.drivers.sales_growth)
    assert all(0.0 <= m <= 0.60 for m in I2.drivers.oper_margin)


def test_news_ingest_respects_min_confidence():
    I = base_inputs()
    V = kernel_value(I)
    items = [NewsItem(id="x", title="Company raises guidance", url="u", source="s", published_at="2025-09-01T00:00:00Z")]
    bundle = NewsBundle(ticker="NWS", asof="2025-09-03T00:00:00Z", items=items)
    summary = heuristic_summarize(bundle, I, scenario={"news": {"caps": {"growth_bps": 50}}})
    # Force low confidence on impacts
    for imp in summary.impacts:
        imp.confidence = 0.2
    I2 = ingest_and_update(I, V, summary, scenario={"news": {"caps": {"growth_bps": 50}, "min_confidence": 0.5}})
    # No changes applied because impacts below threshold
    assert I2.drivers.sales_growth == I.drivers.sales_growth
