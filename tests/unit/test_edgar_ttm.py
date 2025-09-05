from __future__ import annotations

from investing_agent.connectors.edgar import parse_companyfacts_to_fundamentals
from investing_agent.agents.valuation import build_inputs_from_fundamentals


def test_parse_companyfacts_ttm_and_scaling():
    # Quarterly revenue/EBIT in millions, last 4 quarters sum to 12,000 and 3,600 respectively
    cf = {
        "entityName": "TTM Example Corp",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USDm": [
                            {"fy": 2023, "fp": "Q1", "val": 2500, "end": "2023-03-31"},
                            {"fy": 2023, "fp": "Q2", "val": 2800, "end": "2023-06-30"},
                            {"fy": 2023, "fp": "Q3", "val": 3000, "end": "2023-09-30"},
                            {"fy": 2023, "fp": "Q4", "val": 3700, "end": "2023-12-31"},
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USDm": [
                            {"fy": 2023, "fp": "Q1", "val": 700, "end": "2023-03-31"},
                            {"fy": 2023, "fp": "Q2", "val": 800, "end": "2023-06-30"},
                            {"fy": 2023, "fp": "Q3", "val": 900, "end": "2023-09-30"},
                            {"fy": 2023, "fp": "Q4", "val": 1200, "end": "2023-12-31"},
                        ]
                    }
                },
                # Annuals (in thousands) ensure unit scaling works for annual dicts too
                "Revenues_Annual": {
                    "units": {"USDth": [{"fy": 2023, "fp": "FY", "val": 11000000, "end": "2023-12-31"}]}
                },
            }
        },
    }

    # Map custom annual tag for this test
    from investing_agent.connectors.edgar import REVENUE_TAGS
    REVENUE_TAGS.insert(0, "Revenues_Annual")

    f = parse_companyfacts_to_fundamentals(cf, ticker="TTM")

    # TTM should be in USD (millions scaled to absolute)
    assert f.revenue_ttm == 12_000_000_000.0
    assert f.ebit_ttm == 3_600_000_000.0

    # Annual dict should reflect scaling of USDth to USD
    assert f.revenue[2023] == 11_000_000_000.0

    I = build_inputs_from_fundamentals(f, horizon=5)
    # revenue_t0 should prefer TTM over last FY
    assert I.revenue_t0 == 12_000_000_000.0
    # Initial margin should reflect TTM margin (0.3)
    assert abs(I.drivers.oper_margin[0] - 0.3) < 1e-6
