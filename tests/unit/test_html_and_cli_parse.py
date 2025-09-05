from __future__ import annotations

from investing_agent.agents.html_writer import render_html_report
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value
from investing_agent.schemas.fundamentals import Fundamentals


def test_html_writer_basic():
    f = Fundamentals(
        company="HTML Co",
        ticker="HTM",
        currency="USD",
        revenue={2022: 800, 2023: 1000},
        ebit={2022: 80, 2023: 110},
        shares_out=1000.0,
        tax_rate=0.25,
    )
    I = build_inputs_from_fundamentals(f, horizon=4)
    V = value(I)
    html = render_html_report(I, V, fundamentals=f, companyfacts_json={"facts": {"us-gaap": {}}})
    assert "<html" in html and "Per-Year Detail" in html
    assert "Fundamentals (Parsed)" in html
    assert "Raw Companyfacts" in html


def test_parse_path_arg_cli():
    # Import non-public helper (module-level) for convenience
    from scripts.report import _parse_path_arg

    assert _parse_path_arg("8%, 7%,6%") == [0.08, 0.07, 0.06]
    assert _parse_path_arg("0.1,0.05") == [0.1, 0.05]
    assert _parse_path_arg("  ") is None

