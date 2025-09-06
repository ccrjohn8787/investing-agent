from __future__ import annotations

from investing_agent.agents.router import simulate_routes, choose_next


def test_simulate_routes_cycle_all_enabled():
    routes = simulate_routes(have_consensus=True, have_comparables=True, allow_news=True, steps=5)
    # Expect cycle starting with market
    assert routes[:4] == ["market", "consensus", "comparables", "news"]


def test_simulate_routes_cycle_minimal():
    routes = simulate_routes(have_consensus=False, have_comparables=False, allow_news=False, steps=3)
    assert routes == ["market", "market", "market"]


def test_end_conditions():
    class V:
        def __init__(self, vps: float):
            self.value_per_share = vps
    I = object()
    v = V(100.0)
    # Max iters reached
    ctx = {"iter": 10, "max_iters": 10, "unchanged_steps": 0}
    r, _ = choose_next(I, v, ctx)
    assert r == "end"
    # Unchanged steps threshold
    ctx = {"iter": 0, "max_iters": 10, "unchanged_steps": 2}
    r, _ = choose_next(I, v, ctx)
    assert r == "end"
