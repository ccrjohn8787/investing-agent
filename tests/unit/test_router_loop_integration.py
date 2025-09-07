from __future__ import annotations

from investing_agent.agents.router import choose_next
from investing_agent.agents.writer import render_report
from investing_agent.agents.critic import check_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import Discounting, Drivers, InputsI, Macro


class V:
    def __init__(self, vps: float):
        self.value_per_share = vps


def _base_inputs(T: int = 6) -> InputsI:
    return InputsI(
        company="LoopCo",
        ticker="LOOP",
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.05] * T,
            oper_margin=[0.15] * T,
            stable_growth=0.02,
            stable_margin=0.15,
        ),
        sales_to_capital=[2.0] * T,
        wacc=[0.06] * T,
        macro=Macro(risk_free_curve=[0.04] * T, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode="end"),
    )


def test_convergence_gate_sensitivity_once_and_stop():
    # Synthetic ctx with near-convergence across two steps
    I = object()
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
        "within_threshold_steps": 0,
    }
    threshold = 0.005
    unchanged_steps_break = 2

    # Step 1: baseline
    v = V(100.0)
    r, _ = choose_next(I, v, ctx)
    assert r == "market"
    prev = v.value_per_share
    # Step 2: move within threshold
    v.value_per_share = 100.4  # 0.4% delta vs prev
    ctx["last_value"] = prev
    r2, _ = choose_next(I, v, ctx)
    # Near convergence should trigger sensitivity when not run yet
    assert r2 == "sensitivity"
    ctx["ran_sensitivity_recent"] = True
    # Step 3: another small move within threshold
    ctx["within_threshold_steps"] = 1
    prev2 = v.value_per_share
    v.value_per_share = 100.85  # < 0.5% since prev2

    # Critic check using real report
    I_real = _base_inputs(T=6)
    V_real = kernel_value(I_real)
    md = render_report(I_real, V_real)
    issues = check_report(md, I_real, V_real, manifest=None)
    assert not issues

    # Emulate supervisor's gate decision: two within-threshold steps and no blockers should end
    rd = abs(v.value_per_share - prev2) / prev2
    assert rd <= threshold
    within = ctx.get("within_threshold_steps", 0) + 1
    assert within >= unchanged_steps_break
