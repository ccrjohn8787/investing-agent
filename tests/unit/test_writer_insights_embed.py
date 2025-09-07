from __future__ import annotations

import json
from pathlib import Path

from investing_agent.agents.critic import check_report
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.research import InsightBundle
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


def base_inputs(T: int = 6) -> InputsI:
    return InputsI(
        company="InsightCo",
        ticker="INS",
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


def test_writer_embeds_insights_and_critic_passes():
    I = base_inputs()
    # Ensure critic can resolve snaps referenced in cassette
    I.provenance.content_sha256 = "abcd1234"
    V = kernel_value(I)
    data = json.loads(Path("evals/research/cassettes/insights_sample.json").read_text())
    bundle = InsightBundle.model_validate(data)
    md = render_report(I, V, insights=bundle)
    # Section and content present
    assert "## Insights" in md
    assert "Segment A shows improving margins" in md
    assert "Capex intensity trending lower" in md
    assert "[snap:abcd1234]" in md
    # Critic should have zero issues (tokens resolve)
    issues = check_report(md, I, V)
    assert not issues

