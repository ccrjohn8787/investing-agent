from __future__ import annotations

from investing_agent.connectors.ust import build_risk_free_curve_from_ust, latest_yield_curve


def test_latest_yield_curve_and_build_curve():
    rows = [
        {"Date": "2024-09-30", "1 Mo": "5.54", "10 Yr": "4.27"},
        {"Date": "2024-10-01", "1 Mo": "5.55", "10 Yr": "4.30"},
    ]
    curve = latest_yield_curve(rows)
    assert abs(curve["10 yr"] - 0.0430) < 1e-6
    rf = build_risk_free_curve_from_ust(rows, horizon=10)
    assert len(rf) == 10
    assert abs(rf[0] - 0.0430) < 1e-6

