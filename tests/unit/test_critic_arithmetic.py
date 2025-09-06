from __future__ import annotations

from investing_agent.agents.critic import check_report
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value
from investing_agent.schemas.fundamentals import Fundamentals


def test_critic_checks_arithmetic_consistency():
    f = Fundamentals(
        company="ArithCo",
        ticker="ARTH",
        currency="USD",
        revenue={2022: 900, 2023: 1000},
        ebit={2022: 120, 2023: 130},
        shares_out=1000.0,
        tax_rate=0.25,
    )
    I = build_inputs_from_fundamentals(f, horizon=5)
    V = value(I)
    md = render_report(I, V, fundamentals=f)
    issues = check_report(md, I, V)
    # Expect no arithmetic issues for native-rendered report
    assert not any("Inconsistent PV" in x for x in issues)
    assert not any("Equity value check failed" in x for x in issues)

