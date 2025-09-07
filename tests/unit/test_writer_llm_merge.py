from __future__ import annotations

import json
from pathlib import Path

from investing_agent.agents.writer import render_report
from investing_agent.agents.critic import check_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.schemas.writer_llm import WriterLLMOutput


def base_inputs(T: int = 6):
    from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro

    return InputsI(
        company="LLMCo",
        ticker="LLM",
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


def test_merge_llm_sections_and_critic_passes(tmp_path):
    # Build simple inputs and valuation
    f = Fundamentals(company="LLMCo", ticker="LLM", currency="USD", revenue={2023: 1000.0}, ebit={2023: 150.0}, shares_out=1000.0, tax_rate=0.25)
    I = base_inputs(T=6)
    V = kernel_value(I)
    # Load cassette
    cassette = Path("evals/writer_llm/cassettes/sample_output.json")
    data = json.loads(cassette.read_text())
    out = WriterLLMOutput.model_validate(data)
    # Render and merge
    md = render_report(I, V, fundamentals=f, llm_output=out)
    # Sections present
    assert "## Business Model" in md
    assert "## Thesis" in md
    assert "## Risks" in md
    # Core section still present
    assert "## Per-Year Detail" in md
    # Critic passes
    issues = check_report(md, I, V)
    assert not issues, f"Critic issues: {issues}"

