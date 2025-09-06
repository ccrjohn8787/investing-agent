from __future__ import annotations

from investing_agent.agents.critic import check_report
from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.valuation import ValuationV


def make_I_V():
    I = InputsI(
        company="CriticCo",
        ticker="CRT",
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        drivers=Drivers(
            sales_growth=[0.05] * 5,
            oper_margin=[0.15] * 5,
            stable_growth=0.02,
            stable_margin=0.15,
        ),
        sales_to_capital=[2.0] * 5,
        wacc=[0.06] * 5,
    )
    V = ValuationV(
        pv_explicit=500.0,
        pv_terminal=1500.0,
        pv_oper_assets=2000.0,
        equity_value=2000.0,
        shares_out=1000.0,
        value_per_share=2.00,
    )
    # Fake provenance to trigger citations requirement
    I.provenance.source_url = "local://inputs"
    I.provenance.content_sha256 = "abc"
    return I, V


def test_critic_detects_missing_sections_and_citations():
    I, V = make_I_V()
    md = "# Report\n\nValue per share: 2.00\n\n## Per-Year Detail\n...\n"  # missing terminal value, citations
    issues = check_report(md, I, V)
    assert any("Missing section: ## Terminal Value" in x for x in issues)
    assert any("Missing Citations section" in x for x in issues)


def test_critic_passes_complete_report():
    I, V = make_I_V()
    md = (
        f"# Report\n\nValue per share: {V.value_per_share:,.2f}\n- Equity value: {V.equity_value:,.0f}\n- PV (explicit): {V.pv_explicit:,.0f}\n- PV (terminal): {V.pv_terminal:,.0f}\n- Shares out: {V.shares_out:,.0f}\n\n"
        "## Per-Year Detail\n| ... |\n\n## Terminal Value\n...\n\n## Citations\n- EDGAR: local\n"
    )
    issues = check_report(md, I, V)
    assert issues == []

