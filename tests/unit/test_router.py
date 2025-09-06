from __future__ import annotations

from investing_agent.agents.router import choose_next


class V:
    def __init__(self, vps: float):
        self.value_per_share = vps


def test_router_basic_cycle_and_convergence():
    I = object()
    v = V(100.0)
    ctx = {
        "iter": 0,
        "max_iters": 10,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": False,
        "have_consensus": False,
        "have_comparables": False,
        "allow_news": False,
        "last_route": None,
    }
    # First route defaults to market
    r, _ = choose_next(I, v, ctx)
    assert r == "market"
    # If near convergence and sensitivity not run, choose sensitivity
    ctx2 = ctx | {"last_value": 100.2}  # 0.2% away
    r2, _ = choose_next(I, v, ctx2)
    assert r2 == "sensitivity"


def test_router_cycle_with_consensus_and_comps():
    I = object()
    v = V(50.0)
    ctx = {
        "iter": 0,
        "max_iters": 10,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": True,  # already ran
        "have_consensus": True,
        "have_comparables": True,
        "allow_news": False,
        "last_route": None,
    }
    r, _ = choose_next(I, v, ctx)
    assert r == "market"
    ctx["last_route"] = r
    r2, _ = choose_next(I, v, ctx)
    assert r2 == "consensus"
    ctx["last_route"] = r2
    r3, _ = choose_next(I, v, ctx)
    assert r3 == "comparables"

