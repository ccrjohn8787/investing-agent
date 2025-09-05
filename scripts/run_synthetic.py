#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from investing_agent.agents.plotting import plot_driver_paths, plot_sensitivity_heatmap
from investing_agent.agents.sensitivity import compute_sensitivity
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals


def main():
    # Synthetic fundamentals for demo
    f = Fundamentals(
        company="SyntheticCo",
        ticker="SYN",
        currency="USD",
        revenue={2021: 800, 2022: 900, 2023: 1000},
        ebit={2021: 80, 2022: 95, 2023: 110},
        shares_out=1000.0,
        tax_rate=0.25,
        net_debt=0.0,
        cash_nonop=0.0,
    )

    I = build_inputs_from_fundamentals(f, horizon=10)
    V = kernel_value(I)

    # Sensitivity + plots
    sens = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(5, 5))
    heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {I.ticker}")

    import numpy as np

    g = np.array(I.drivers.sales_growth)
    m = np.array(I.drivers.oper_margin)
    w = np.array(I.wacc)
    drv_png = plot_driver_paths(len(g), g, m, w)

    md = render_report(I, V, sensitivity_png=heat_png, driver_paths_png=drv_png)

    out = Path("out")
    out.mkdir(exist_ok=True)
    (out / f"{I.ticker}_report.md").write_text(md)
    (out / f"{I.ticker}_sensitivity.png").write_bytes(heat_png)
    (out / f"{I.ticker}_drivers.png").write_bytes(drv_png)
    print(f"Wrote report and plots to {out.resolve()}")


if __name__ == "__main__":
    main()

