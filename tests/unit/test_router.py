from __future__ import annotations

from investing_agent.agents.router import choose_next
from investing_agent.schemas.valuation import ValuationV


def V(vps: float) -> ValuationV:
    return ValuationV(
        pv_explicit=1.0,
        pv_terminal=1.0,
        pv_oper_assets=2.0,
        equity_value=vps,
        shares_out=1.0,
        value_per_share=vps,
    )


def test_router_iter_cap_ends():
    r, _ = choose_next(None, V(10.0), {"iter": 10, "max_iters": 10})
    assert r == "end"


def test_router_unchanged_steps_ends():
    r, _ = choose_next(None, V(10.0), {"unchanged_steps": 2})
    assert r == "end"


def test_router_triggers_sensitivity_when_close_to_converged():
    r, _ = choose_next(None, V(100.0), {"last_value": 100.4, "ran_sensitivity_recent": False})
    assert r == "sensitivity"


def test_router_cycle_order():
    ctx = {"have_consensus": True, "have_comparables": True, "allow_news": False}
    r1, _ = choose_next(None, V(10.0), {**ctx, "last_route": None})
    r2, _ = choose_next(None, V(10.0), {**ctx, "last_route": r1})
    r3, _ = choose_next(None, V(10.0), {**ctx, "last_route": r2})
    assert r1 == "market"
    assert r2 == "consensus"
    assert r3 == "comparables"

