from __future__ import annotations

from investing_agent.connectors.edgar import parse_companyfacts_to_fundamentals


def test_parse_additional_fundamentals_tags():
    cf = {
        "entityName": "Lease & Capex Corp",
        "facts": {
            "us-gaap": {
                # Depreciation & Amortization in millions
                "DepreciationDepletionAndAmortization": {
                    "units": {
                        "USDm": [
                            {"fy": 2022, "fp": "FY", "val": 900, "end": "2022-12-31"},
                            {"fy": 2023, "fp": "FY", "val": 950, "end": "2023-12-31"},
                        ]
                    }
                },
                # Capex in thousands (negative cash outflow)
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USDth": [
                            {"fy": 2023, "fp": "FY", "val": -1200000, "end": "2023-12-31"}
                        ]
                    }
                },
                # Lease assets and split liabilities in USD
                "OperatingLeaseRightOfUseAsset": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "val": 500000000, "end": "2023-12-31"}
                        ]
                    }
                },
                "OperatingLeaseLiabilityCurrent": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "val": 100000000, "end": "2023-12-31"}
                        ]
                    }
                },
                "OperatingLeaseLiabilityNoncurrent": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "val": 300000000, "end": "2023-12-31"}
                        ]
                    }
                },
            }
        },
    }

    f = parse_companyfacts_to_fundamentals(cf, ticker="LCX")
    # Scaling: USDm -> 1e6; USDth -> 1e3
    assert f.dep_amort[2023] == 950_000_000.0
    assert f.capex[2023] == -1_200_000_000.0
    assert f.lease_assets[2023] == 500_000_000.0
    # Liabilities sum of current + noncurrent
    assert f.lease_liabilities[2023] == 400_000_000.0

