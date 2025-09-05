from __future__ import annotations

from pathlib import Path

from investing_agent.schemas.fundamentals import Fundamentals


def test_write_fundamentals_csv(tmp_path: Path):
    from scripts.report import _write_fundamentals_csv

    f = Fundamentals(
        company="CSVCo",
        ticker="CSV",
        revenue={2023: 1000.0},
        ebit={2023: 120.0},
        dep_amort={2023: 50.0},
        capex={2023: -80.0},
        lease_assets={2023: 200.0},
        lease_liabilities={2023: 150.0},
        current_assets={2023: 400.0},
        current_liabilities={2023: 250.0},
    )
    p = tmp_path / "fundamentals.csv"
    _write_fundamentals_csv(p, f)
    text = p.read_text()
    assert "year,revenue,ebit,dep_amort,capex,lease_assets,lease_liabilities,current_assets,current_liabilities" in text.replace(" ", "")
    assert ",1000.0,120.0,50.0,-80.0,200.0,150.0,400.0,250.0" in text

