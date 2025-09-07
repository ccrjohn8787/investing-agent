from __future__ import annotations

from investing_agent.orchestration.fsm import Context, State, step


def test_convergence_counter_and_stop_condition_like_behavior():
    ctx = Context(delta_value_threshold=0.005, unchanged_steps_break=2, max_iters=10)
    s = State(iter=0, last_value=None, ran_sensitivity_recent=True)  # already ran
    # Step 1 -> near threshold increments counter
    s, a1, _ = step(s, ctx, 100.0)
    s.last_value = 100.0
    s, a2, _ = step(s, ctx, 100.4)  # 0.4%
    assert s.within_threshold_steps >= 1
    # Step 2 -> still within threshold increments
    prev = s.within_threshold_steps
    s, a3, _ = step(s, ctx, 100.85)  # <0.5%
    assert s.within_threshold_steps >= prev

