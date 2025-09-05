from __future__ import annotations

import json
from pathlib import Path

from investing_agent.connectors.edgar import parse_companyfacts_to_fundamentals
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value
from investing_agent.agents.writer import render_report
from investing_agent.schemas.inputs import Macro, Discounting


def test_canary_min_pipeline(tmp_path: Path):
    # Load minimal companyfacts fixture
    cf_path = Path(__file__).parent.parent / "fixtures" / "companyfacts_canary_min.json"
    cf = json.loads(cf_path.read_text())
    f = parse_companyfacts_to_fundamentals(cf, ticker="CNY")

    # Deterministic macro and settings
    horizon = 5
    macro = Macro(risk_free_curve=[0.04] * horizon, erp=0.05, country_risk=0.0)
    I = build_inputs_from_fundamentals(
        f,
        horizon=horizon,
        stable_growth=0.03,
        stable_margin=0.18,
        macro=macro,
        discounting=Discounting(mode="end"),
    )
    V = value(I)

    # Sanity: PV bridge, positive value per share
    assert abs((V.pv_explicit + V.pv_terminal) - V.pv_oper_assets) < 1e-6
    assert V.value_per_share > 0

    # Writer output contains expected sections
    md = render_report(I, V)
    assert "## Per-Year Detail" in md
    assert "## Terminal Value" in md

