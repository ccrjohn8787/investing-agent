from __future__ import annotations

from investing_agent.connectors.edgar import parse_companyfacts_to_fundamentals


def test_ifrs_parse_revenue_ebit_shares_tax_and_wc():
    cf = {
        "entityName": "IFRS Co",
        "facts": {
            "ifrs-full": {
                "Revenue": {
                    "units": {
                        "USDm": [
                            {"fy": 2022, "fp": "FY", "val": 900, "end": "2022-12-31"},
                            {"fy": 2023, "fp": "FY", "val": 1000, "end": "2023-12-31"},
                        ]
                    }
                },
                "OperatingProfitLoss": {
                    "units": {
                        "USDm": [
                            {"fy": 2022, "fp": "FY", "val": 180, "end": "2022-12-31"},
                            {"fy": 2023, "fp": "FY", "val": 200, "end": "2023-12-31"},
                        ]
                    }
                },
                "NumberOfSharesOutstanding": {
                    "units": {"shares": [{"fy": 2023, "fp": "FY", "val": 1000, "end": "2023-12-31"}]}
                },
                "EffectiveTaxRate": {
                    "units": {"pure": [{"fy": 2023, "fp": "FY", "val": 0.23, "end": "2023-12-31"}]}
                },
                "CurrentAssets": {
                    "units": {"USD": [{"fy": 2023, "fp": "FY", "val": 1500000000, "end": "2023-12-31"}]}
                },
                "CurrentLiabilities": {
                    "units": {"USD": [{"fy": 2023, "fp": "FY", "val": 500000000, "end": "2023-12-31"}]}
                },
            }
        },
    }
    f = parse_companyfacts_to_fundamentals(cf, ticker="IFR")
    assert f.revenue[2023] == 1_000_000_000.0
    assert f.ebit[2023] == 200_000_000.0
    assert f.shares_out == 1000
    assert f.tax_rate and abs(f.tax_rate - 0.23) < 1e-9
    assert f.current_assets[2023] == 1_500_000_000.0
    assert f.current_liabilities[2023] == 500_000_000.0

