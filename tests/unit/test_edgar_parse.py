from __future__ import annotations

from investing_agent.connectors.edgar import parse_companyfacts_to_fundamentals


def test_parse_companyfacts_minimal():
    cf = {
        "entityName": "Example Corp",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"fy": 2022, "fp": "FY", "val": 1000, "end": "2022-12-31"},
                            {"fy": 2023, "fp": "FY", "val": 1100, "end": "2023-12-31"},
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2022, "fp": "FY", "val": 120, "end": "2022-12-31"},
                            {"fy": 2023, "fp": "FY", "val": 150, "end": "2023-12-31"},
                        ]
                    }
                },
                "CommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"fy": 2023, "fp": "FY", "val": 100.0, "end": "2023-12-31"}
                        ]
                    }
                },
                "EffectiveIncomeTaxRate": {
                    "units": {
                        "pure": [
                            {"fy": 2023, "fp": "FY", "val": 0.21, "end": "2023-12-31"}
                        ]
                    }
                },
            }
        },
    }

    f = parse_companyfacts_to_fundamentals(cf, ticker="EX")
    assert f.company == "Example Corp"
    assert f.revenue[2023] == 1100
    assert f.ebit[2023] == 150
    assert f.shares_out == 100.0
    assert 0.0 <= (f.tax_rate or 0.0) <= 0.6

