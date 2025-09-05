#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from investing_agent.agents.router import choose_next
from investing_agent.agents.sensitivity import compute_sensitivity
from investing_agent.agents.plotting import plot_sensitivity_heatmap, plot_driver_paths
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.market import apply as apply_market
from investing_agent.agents.consensus import apply as apply_consensus
from investing_agent.agents.comparables import apply as apply_comparables
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals


def main():
    f = Fundamentals(
        company="RouterDemo",
        ticker="RDEMO",
        currency="USD",
        revenue={2022: 800, 2023: 1000},
        ebit={2022: 80, 2023: 110},
        shares_out=1000.0,
        tax_rate=0.25,
    )
    I = build_inputs_from_fundamentals(f, horizon=8)
    V = kernel_value(I)

    ctx = {
        "iter": 0,
        "max_iters": 5,
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": False,
        "have_consensus": True,
        "have_comparables": True,
        "allow_news": False,
        "last_route": None,
    }

    figures = None
    import numpy as np

    while True:
        route, _ = choose_next(I, V, ctx)
        if route == "end":
            break
        prev_v = V.value_per_share
        if route == "market":
            I = apply_market(I)
        elif route == "consensus":
            I = apply_consensus(I)
        elif route == "comparables":
            I = apply_comparables(I)
        elif route == "sensitivity":
            sens = compute_sensitivity(I)
            heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {I.ticker}")
            g = np.array(I.drivers.sales_growth)
            m = np.array(I.drivers.oper_margin)
            w = np.array(I.wacc)
            drv_png = plot_driver_paths(len(g), g, m, w)
            figures = (heat_png, drv_png)
            ctx["ran_sensitivity_recent"] = True
        V = kernel_value(I)
        ctx["iter"] += 1
        ctx["last_route"] = route
        if prev_v is not None and prev_v == V.value_per_share:
            ctx["unchanged_steps"] = ctx.get("unchanged_steps", 0) + 1
        else:
            ctx["unchanged_steps"] = 0
        ctx["last_value"] = prev_v

    heat_png, drv_png = figures if figures else (None, None)
    md = render_report(I, V, sensitivity_png=heat_png, driver_paths_png=drv_png, fundamentals=f)
    out = Path("out")
    out.mkdir(exist_ok=True)
    (out / f"{I.ticker}_router_demo.md").write_text(md)
    if heat_png:
        (out / f"{I.ticker}_router_sensitivity.png").write_bytes(heat_png)
    if drv_png:
        (out / f"{I.ticker}_router_drivers.png").write_bytes(drv_png)
    print("Router demo complete. Artifacts in ./out/")


if __name__ == "__main__":
    main()

