from __future__ import annotations

from investing_agent.orchestration.fsm import Context, State, step, run


def test_route_sequence_flags():
    ctx = Context(have_consensus=True, have_comparables=True, allow_news=True, max_iters=5)
    s = State(iter=0, last_route=None, ran_sensitivity_recent=True)  # avoid sens trigger
    # value path not near convergence
    vals = [100.0, 102.0, 101.0, 100.5, 100.2]
    res = run(s, ctx, vals)
    # Expect cycle: market -> consensus -> comparables -> news -> market
    assert res.steps[:4] == ["market", "consensus", "comparables", "news"]


def test_sensitivity_once_near_convergence():
    ctx = Context(have_consensus=False, have_comparables=False, allow_news=False, max_iters=3)
    s = State(iter=0, last_route=None, ran_sensitivity_recent=False)
    # First step arbitrary, then small delta triggers sensitivity once
    vals = [100.0, 100.4, 100.3]
    res = run(s, ctx, vals)
    assert "sensitivity" in res.steps

