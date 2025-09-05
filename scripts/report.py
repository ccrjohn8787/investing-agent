#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from investing_agent.agents.plotting import plot_driver_paths, plot_sensitivity_heatmap
from investing_agent.agents.sensitivity import compute_sensitivity
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.writer import render_report
from investing_agent.connectors.edgar import (
    fetch_companyfacts,
    parse_companyfacts_to_fundamentals,
)
from investing_agent.connectors.stooq import fetch_prices as fetch_prices_stooq
from investing_agent.connectors.yahoo import fetch_prices_v8_chart
from investing_agent.connectors.ust import (
    build_risk_free_curve_from_ust,
    fetch_treasury_yield_csv,
)
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import InputsI


def main():
    ap = argparse.ArgumentParser(description="Generate valuation report for a ticker.")
    ap.add_argument("ticker", nargs="?", default=os.environ.get("CT") or os.environ.get("TICKER"))
    ap.add_argument("--fresh", action="store_true", help="Bypass cached inputs and fetch live fundamentals")
    args = ap.parse_args()
    if not args.ticker:
        raise SystemExit("Provide ticker as arg or set CT/TICKER")

    ticker = args.ticker.upper()
    # Offline-first: if local inputs exist, use them and skip network
    out_dir = Path("out") / ticker
    local_inputs = out_dir / "inputs.json"
    if local_inputs.exists() and not args.fresh:
        I = InputsI.model_validate_json(local_inputs.read_text())
        if not I.macro.risk_free_curve:
            I.macro.risk_free_curve = [0.03] * I.horizon()
        cf_json = {}
    else:
        edgar_ua = os.environ.get("EDGAR_UA")
        if not edgar_ua:
            print("Warning: EDGAR_UA not set; SEC requests may be blocked.")

        # Fetch fundamentals
        cf_json, meta = fetch_companyfacts(ticker, edgar_ua=edgar_ua)
        f = parse_companyfacts_to_fundamentals(cf_json, ticker=ticker)

        # Macro risk-free from UST latest 10Y
        rows = fetch_treasury_yield_csv()
        rf_curve = build_risk_free_curve_from_ust(rows, horizon=10)

        # Build inputs with macro so WACC path reflects latest rf
        from investing_agent.schemas.inputs import Macro

        macro = Macro(risk_free_curve=rf_curve, erp=0.05, country_risk=0.0)
        I = build_inputs_from_fundamentals(f, horizon=10, macro=macro)

    V = kernel_value(I)

    # Try prices via Stooq; fallback to Yahoo
    try:
        ps = fetch_prices_stooq(ticker)
    except Exception:
        ps = fetch_prices_v8_chart(ticker)
    last_close = ps.bars[-1].close if ps.bars else None

    sens = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(5, 5))
    heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {ticker}")

    import numpy as np

    g = np.array(I.drivers.sales_growth)
    m = np.array(I.drivers.oper_margin)
    w = np.array(I.wacc)
    drv_png = plot_driver_paths(len(g), g, m, w)

    md = render_report(I, V, sensitivity_png=heat_png, driver_paths_png=drv_png)
    if last_close is not None:
        md += f"\n\n## Market\n- Last close: {last_close:,.2f}\n- Discount/Premium vs value: {(V.value_per_share/last_close - 1.0):.2%}\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    if cf_json:
        (out_dir / "companyfacts.json").write_text(json.dumps(cf_json))
    (out_dir / "report.md").write_text(md)
    (out_dir / "sensitivity.png").write_bytes(heat_png)
    (out_dir / "drivers.png").write_bytes(drv_png)
    print(f"Wrote report to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
