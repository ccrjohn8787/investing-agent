from __future__ import annotations

"""
Router agent (planned)

Deterministic rule-based router that chooses the next step among
{market, consensus, comparables, sensitivity, news, end} based on simple heuristics
(e.g., recent changes in I/v, availability of new data, critic feedback).

LLM router optional (temp=0, top_p=1, seed=2025) but proposals must flow through
bounded, schema-checked code paths.
"""

from typing import Dict, Tuple, List


def _rel_delta(curr: float, prev: float | None) -> float | None:
    if prev is None or prev == 0:
        return None
    return abs(curr - prev) / abs(prev)


def _next_in_cycle(last: str | None, options: List[str]) -> str:
    if not options:
        return "end"
    if last not in options:
        return options[0]
    idx = options.index(last)
    return options[(idx + 1) % len(options)]


def choose_next(I, v, context: Dict) -> Tuple[str, str | None]:
    """Return (route, instruction) using deterministic heuristics.

    route in {"market", "consensus", "comparables", "sensitivity", "news", "end"}.
    Context keys (all optional):
      - iter: int (default 0)
      - max_iters: int (default 10)
      - last_value: float | None
      - unchanged_steps: int (default 0)
      - ran_sensitivity_recent: bool (default False)
      - have_consensus: bool (default False)
      - have_comparables: bool (default False)
      - allow_news: bool (default False)
      - last_route: str | None
    """
    it = int(context.get("iter", 0))
    it_cap = int(context.get("max_iters", 10))
    if it >= it_cap:
        return "end", None

    if int(context.get("unchanged_steps", 0)) >= 2:
        return "end", None

    last_v = context.get("last_value")
    curr_v = float(getattr(v, "value_per_share", 0.0))
    rd = _rel_delta(curr_v, last_v)
    ran_sens = bool(context.get("ran_sensitivity_recent", False))
    if rd is not None and rd <= 0.005:
        # Close to convergence: run sensitivity once if not done recently; else end
        if not ran_sens:
            return "sensitivity", None
        # If sensitivity already ran recently, allow one more pass through the cycle

    have_consensus = bool(context.get("have_consensus", False))
    have_comps = bool(context.get("have_comparables", False))
    allow_news = bool(context.get("allow_news", False))
    cycle: List[str] = ["market"]
    if have_consensus:
        cycle.append("consensus")
    if have_comps:
        cycle.append("comparables")
    if allow_news:
        cycle.append("news")

    # If no options besides possibly news, still follow cycle
    last_route = context.get("last_route")
    nxt = _next_in_cycle(last_route, cycle)
    return nxt, None


def simulate_routes(have_consensus: bool, have_comparables: bool, allow_news: bool, steps: int = 5) -> List[str]:
    """Utility for tests: simulate next routes for a few steps given gating flags."""
    routes: List[str] = []
    ctx = {
        "iter": 0,
        "max_iters": steps,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": True,  # avoid sensitivity by default
        "have_consensus": have_consensus,
        "have_comparables": have_comparables,
        "allow_news": allow_news,
        "last_route": None,
    }
    class _V:
        value_per_share = 1.0
    v = _V()
    I = object()
    for _ in range(steps):
        r, _ = choose_next(I, v, ctx)
        if r == "end":
            break
        routes.append(r)
        ctx["last_route"] = r
        ctx["iter"] += 1
    return routes
