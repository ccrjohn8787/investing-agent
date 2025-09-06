from __future__ import annotations

from investing_agent.agents.writer import render_report
from investing_agent.agents.critic import check_report
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value
from investing_agent.schemas.fundamentals import Fundamentals


def _mk_inputs_and_value():
    f = Fundamentals(
        company="RefCo",
        ticker="REF",
        currency="USD",
        revenue={2022: 800, 2023: 1000},
        ebit={2022: 80, 2023: 110},
        shares_out=1000.0,
        tax_rate=0.25,
    )
    I = build_inputs_from_fundamentals(f, horizon=4, stable_growth=0.02, stable_margin=0.12)
    # Add provenance content sha to allow snap ref resolution
    I.provenance.content_sha256 = "abc123"
    V = value(I)
    return I, V


def test_writer_includes_reference_tokens_and_critic_resolves():
    I, V = _mk_inputs_and_value()
    # Provide at least one citation to satisfy Critic's citations requirement
    md = render_report(I, V, citations=[f"EDGAR snapshot {I.provenance.content_sha256}"])
    # Summary should include inline [ref: ...] tokens
    assert "[ref:" in md
    assert "table:Per-Year Detail" in md
    assert "section:Terminal Value" in md
    # Critic should find no issues for a complete report with valid refs
    issues = check_report(md, I, V)
    assert issues == []


def test_critic_flags_unresolved_snapshot_reference():
    I, V = _mk_inputs_and_value()
    md = render_report(I, V, citations=[f"EDGAR snapshot {I.provenance.content_sha256}"])
    # Corrupt the snap reference to an unknown sha
    bad_md = md.replace(f"snap:{I.provenance.content_sha256}", "snap:deadbeef")
    issues = check_report(bad_md, I, V)
    assert any("Unresolved reference: snap:deadbeef" in s for s in issues)

