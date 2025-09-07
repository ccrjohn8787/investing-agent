from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class Context:
    delta_value_threshold: float = 0.005
    unchanged_steps_break: int = 2
    have_consensus: bool = False
    have_comparables: bool = False
    allow_news: bool = False
    max_iters: int = 10


@dataclass
class State:
    iter: int = 0
    last_route: Optional[str] = None
    last_value: Optional[float] = None
    ran_sensitivity_recent: bool = False
    within_threshold_steps: int = 0


def _rel_delta(curr: float, prev: Optional[float]) -> Optional[float]:
    if prev is None or prev == 0:
        return None
    return abs(curr - prev) / abs(prev)


def _cycle(last: Optional[str], options: List[str]) -> str:
    if not options:
        return "end"
    if last not in options:
        return options[0]
    i = options.index(last)
    return options[(i + 1) % len(options)]


def step(state: State, ctx: Context, curr_value_per_share: float) -> Tuple[State, str, str]:
    """Single FSM step: returns (next_state, action, notes). action in {market, consensus, comparables, news, sensitivity, end}."""
    notes = ""
    if state.iter >= ctx.max_iters:
        return state, "end", "max_iters"

    # Near convergence trigger for sensitivity once
    rd = _rel_delta(curr_value_per_share, state.last_value)
    if rd is not None and rd <= ctx.delta_value_threshold:
        state.within_threshold_steps += 1
        if not state.ran_sensitivity_recent:
            state.iter += 1
            state.last_route = "sensitivity"
            state.ran_sensitivity_recent = True
            return state, "sensitivity", "near_convergence_sensitivity"
    else:
        state.within_threshold_steps = 0

    # Route cycle
    options: List[str] = ["market"]
    if ctx.have_consensus:
        options.append("consensus")
    if ctx.have_comparables:
        options.append("comparables")
    if ctx.allow_news:
        options.append("news")
    action = _cycle(state.last_route, options)

    state.iter += 1
    state.last_route = action
    state.last_value = curr_value_per_share
    return state, action, notes


@dataclass
class RunResult:
    steps: List[str]
    final_state: State


def run(initial_state: State, ctx: Context, value_path: List[float]) -> RunResult:
    """Run the FSM for up to len(value_path) steps, using supplied values to compute near-convergence decisions."""
    s = initial_state
    seq: List[str] = []
    for v in value_path:
        s, action, _ = step(s, ctx, v)
        if action == "end":
            break
        seq.append(action)
    return RunResult(steps=seq, final_state=s)

