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
from investing_agent.agents.html_writer import render_html_report
from investing_agent.connectors.edgar import (
    fetch_companyfacts,
    parse_companyfacts_to_fundamentals,
)
from investing_agent.connectors.stooq import fetch_prices as fetch_prices_stooq
from investing_agent.connectors.stooq import _stooq_url_us as _stooq_url_us  # internal helper
from investing_agent.connectors.stooq import fetch_prices_with_meta as fetch_prices_stooq_with_meta
from investing_agent.connectors.yahoo import fetch_prices_v8_chart
from investing_agent.connectors.yahoo import fetch_prices_v8_chart_with_meta
from investing_agent.connectors.ust import (
    build_risk_free_curve_from_ust,
    fetch_treasury_yield_csv,
    fetch_treasury_yield_csv_with_meta,
)
from investing_agent.connectors import ust as ust_mod
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.orchestration.eventlog import EventLog
from investing_agent.orchestration.manifest import Manifest, Snapshot
import time as _time
import hashlib as _hashlib


def _parse_path_arg(s: str | None) -> list[float] | None:
    if not s:
        return None
    out = []
    for part in s.split(","):
        p = part.strip()
        if not p:
            continue
        is_pct = p.endswith("%")
        if is_pct:
            p = p[:-1]
        val = float(p)
        if is_pct or abs(val) > 1.0:
            val = val / 100.0
        out.append(val)
    return out or None

def _load_config(path: Path) -> dict:
    try:
        text = path.read_text()
    except Exception as e:
        print(f"Warning: cannot read config: {e}")
        return {}
    # Choose parser by extension; fall back between JSON/YAML
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore

            return yaml.safe_load(text) or {}
        except Exception as e:
            print(f"Warning: YAML config load failed: {e}")
            try:
                return json.loads(text)
            except Exception:
                return {}
    else:
        try:
            return json.loads(text)
        except Exception as e:
            # try YAML as a fallback
            try:
                import yaml  # type: ignore

                return yaml.safe_load(text) or {}
            except Exception:
                print(f"Warning: JSON config load failed: {e}")
                return {}


def _write_series_csv(path: Path, I: InputsI):
    from investing_agent.kernels import ginzu as K
    import csv

    S = K.series(I)
    rev = S.revenue
    ebit = S.ebit
    fcff = S.fcff
    wacc = S.wacc
    df = S.discount_factors
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "revenue", "ebit", "fcff", "wacc", "df", "pv_fcff"])
        for t in range(len(rev)):
            w.writerow([
                t + 1,
                f"{float(rev[t]):.6f}",
                f"{float(ebit[t]):.6f}",
                f"{float(fcff[t]):.6f}",
                f"{float(wacc[t]):.6f}",
                f"{float(df[t]):.6f}",
                f"{float(fcff[t]*df[t]):.6f}",
            ])

def _write_fundamentals_csv(path: Path, f):
    import csv
    years = set()
    for d in [
        f.revenue,
        f.ebit,
        f.dep_amort,
        f.capex,
        f.lease_assets,
        f.lease_liabilities,
        f.current_assets,
        f.current_liabilities,
    ]:
        years.update(d.keys())
    years = sorted(int(y) for y in years)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "year",
            "revenue",
            "ebit",
            "dep_amort",
            "capex",
            "lease_assets",
            "lease_liabilities",
            "current_assets",
            "current_liabilities",
        ])
        for y in years:
            w.writerow([
                y,
                f.revenue.get(y, ""),
                f.ebit.get(y, ""),
                f.dep_amort.get(y, ""),
                f.capex.get(y, ""),
                f.lease_assets.get(y, ""),
                f.lease_liabilities.get(y, ""),
                f.current_assets.get(y, ""),
                f.current_liabilities.get(y, ""),
            ])


def main():
    ap = argparse.ArgumentParser(description="Generate valuation report for a ticker.")
    ap.add_argument("ticker", nargs="?", default=os.environ.get("CT") or os.environ.get("TICKER"))
    ap.add_argument("--fresh", action="store_true", help="Bypass cached inputs and fetch live fundamentals")
    ap.add_argument("--growth", help="Comma-separated growth overrides (e.g., '8%,7%,6%' or '0.08,0.07')")
    ap.add_argument("--margin", help="Comma-separated margin overrides (e.g., '12%,13%' or '0.12,0.13')")
    ap.add_argument("--s2c", help="Comma-separated sales-to-capital overrides (e.g., '2.0,2.2,2.4')")
    ap.add_argument("--config", help="JSON file with overrides and settings (growth, margin, s2c, stable_*, beta, discounting, horizon, macro)")
    ap.add_argument("--html", action="store_true", help="Also write HTML report next to Markdown")
    args = ap.parse_args()
    if not args.ticker:
        raise SystemExit("Provide ticker as arg or set CT/TICKER")

    ticker = args.ticker.upper()
    run_id = _time.strftime("%Y%m%dT%H%M%SZ", _time.gmtime())
    # Load config file if provided
    cfg = {}
    if args.config:
        cfg = _load_config(Path(args.config))

    # Optional overrides from CLI (take precedence over config)
    growth_path = _parse_path_arg(args.growth) or cfg.get("growth")
    margin_path = _parse_path_arg(args.margin) or cfg.get("margin")
    s2c_path = _parse_path_arg(args.s2c) or cfg.get("s2c")
    cfg_horizon = int(cfg.get("horizon")) if cfg.get("horizon") else None
    cfg_beta = float(cfg.get("beta")) if cfg.get("beta") is not None else None
    cfg_stable_growth = cfg.get("stable_growth")
    cfg_stable_margin = cfg.get("stable_margin")
    cfg_discounting = cfg.get("discounting")
    cfg_macro = cfg.get("macro") or {}

    # Offline-first: if local inputs exist, use them and skip network
    out_dir = Path("out") / ticker
    local_inputs = out_dir / "inputs.json"
    eventlog = EventLog(out_dir / "run.jsonl")
    manifest = Manifest(run_id=run_id, ticker=ticker, asof=None)
    if local_inputs.exists() and not args.fresh:
        I = InputsI.model_validate_json(local_inputs.read_text())
        if not I.macro.risk_free_curve:
            I.macro.risk_free_curve = [0.03] * I.horizon()
        cf_json = {}
        f_for_report: Fundamentals | None = None
        cf_for_report: dict | None = None
        # Try to load local companyfacts for a fundamentals section and to re-build with overrides if any
        local_cf = out_dir / "companyfacts.json"
        if local_cf.exists():
            try:
                cf_json_cached = json.loads(local_cf.read_text())
                f_for_report = parse_companyfacts_to_fundamentals(cf_json_cached, ticker=ticker)
                cf_for_report = cf_json_cached
                # Rebuild inputs when any overrides in either CLI or config
                if any([growth_path, margin_path, s2c_path, cfg_horizon, cfg_beta, cfg_stable_growth, cfg_stable_margin, cfg_discounting, cfg_macro]):
                    horizon = cfg_horizon or I.horizon()
                    # discounting
                    disc = I.discounting
                    if cfg_discounting in ("end", "midyear"):
                        from investing_agent.schemas.inputs import Discounting

                        disc = Discounting(mode=cfg_discounting)
                    # macro
                    macro = I.macro
                    if cfg_macro:
                        from investing_agent.schemas.inputs import Macro

                        mrf = cfg_macro.get("risk_free_curve") or macro.risk_free_curve
                        merp = cfg_macro.get("erp", macro.erp)
                        mcr = cfg_macro.get("country_risk", macro.country_risk)
                        macro = Macro(risk_free_curve=mrf, erp=float(merp), country_risk=float(mcr))
                    I = build_inputs_from_fundamentals(
                        f_for_report,
                        horizon=horizon,
                        stable_growth=cfg_stable_growth,
                        stable_margin=cfg_stable_margin,
                        beta=(cfg_beta if cfg_beta is not None else 1.0),
                        macro=macro,
                        discounting=disc,
                        sales_growth_path=growth_path,
                        oper_margin_path=margin_path,
                        sales_to_capital_path=s2c_path,
                    )
            except Exception:
                pass
    else:
        edgar_ua = os.environ.get("EDGAR_UA")
        if not edgar_ua:
            print("Warning: EDGAR_UA not set; SEC requests may be blocked.")

        # Fetch fundamentals
        t0 = _time.time()
        cf_json, meta = fetch_companyfacts(ticker, edgar_ua=edgar_ua)
        eventlog.log(agent="fetch_fundamentals", params={"ticker": ticker}, outputs=meta, duration_ms=int((_time.time()-t0)*1000))
        manifest.add_snapshot(Snapshot(source="edgar", url=meta.get("source_url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256")))
        f = parse_companyfacts_to_fundamentals(cf_json, ticker=ticker)

        # Macro risk-free from UST latest 10Y with metadata
        rows, ust_meta = fetch_treasury_yield_csv_with_meta()
        manifest.add_snapshot(Snapshot(source="ust", url=ust_meta.get("url"), retrieved_at=ust_meta.get("retrieved_at"), content_sha256=ust_meta.get("content_sha256")))
        rf_curve = build_risk_free_curve_from_ust(rows, horizon=10)

        # Build inputs with macro so WACC path reflects latest rf
        from investing_agent.schemas.inputs import Macro

        macro = Macro(risk_free_curve=rf_curve, erp=0.05, country_risk=0.0)
        horizon = cfg_horizon or 10
        disc = None
        if cfg_discounting in ("end", "midyear"):
            from investing_agent.schemas.inputs import Discounting

            disc = Discounting(mode=cfg_discounting)
        if cfg_macro:
            from investing_agent.schemas.inputs import Macro

            mrf = cfg_macro.get("risk_free_curve") or macro.risk_free_curve
            merp = cfg_macro.get("erp", macro.erp)
            mcr = cfg_macro.get("country_risk", macro.country_risk)
            macro = Macro(risk_free_curve=mrf, erp=float(merp), country_risk=float(mcr))
        t0 = _time.time()
        I = build_inputs_from_fundamentals(
            f,
            horizon=horizon,
            stable_growth=cfg_stable_growth,
            stable_margin=cfg_stable_margin,
            beta=(cfg_beta if cfg_beta is not None else 1.0),
            macro=macro,
            discounting=disc,
            sales_growth_path=growth_path,
            oper_margin_path=margin_path,
            sales_to_capital_path=s2c_path,
        )
        eventlog.log(agent="build_inputs", params={"horizon": horizon}, inputs=f.model_dump(), outputs=I.model_dump(), duration_ms=int((_time.time()-t0)*1000))
        manifest.add_artifact("inputs", I.model_dump())
        f_for_report = f
        cf_for_report = cf_json

    t0 = _time.time()
    V = kernel_value(I)
    eventlog.log(agent="valuation", inputs=I.model_dump(), outputs=V.model_dump(), duration_ms=int((_time.time()-t0)*1000))
    manifest.add_artifact("valuation", V.model_dump())

    # Try prices via Stooq; fallback to Yahoo, with snapshot metadata
    stooq_meta = None
    yahoo_meta = None
    try:
        t0 = _time.time()
        ps, stooq_meta = fetch_prices_stooq_with_meta(ticker)
        eventlog.log(agent="prices", params={"source": "stooq"}, outputs={"bars": len(ps.bars)}, duration_ms=int((_time.time()-t0)*1000))
        manifest.add_snapshot(Snapshot(source="stooq", url=stooq_meta.get("url"), retrieved_at=stooq_meta.get("retrieved_at"), content_sha256=stooq_meta.get("content_sha256")))
    except Exception:
        t0 = _time.time()
        ps, yahoo_meta = fetch_prices_v8_chart_with_meta(ticker)
        eventlog.log(agent="prices", params={"source": "yahoo"}, outputs={"bars": len(ps.bars)}, duration_ms=int((_time.time()-t0)*1000))
        manifest.add_snapshot(Snapshot(source="yahoo", url=yahoo_meta.get("url"), retrieved_at=yahoo_meta.get("retrieved_at"), content_sha256=yahoo_meta.get("content_sha256")))
    last_close = ps.bars[-1].close if ps.bars else None

    t0 = _time.time()
    sens = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(5, 5))
    heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {ticker}")
    eventlog.log(agent="sensitivity", params={"steps": (5,5)}, outputs={"grid": [len(sens.margin_axis), len(sens.growth_axis)]}, duration_ms=int((_time.time()-t0)*1000))

    import numpy as np

    g = np.array(I.drivers.sales_growth)
    m = np.array(I.drivers.oper_margin)
    w = np.array(I.wacc)
    drv_png = plot_driver_paths(len(g), g, m, w)

    # Build citations for report
    citations: list[str] = []
    try:
        if cf_json:
            citations.append(f"EDGAR companyfacts: {meta.get('source_url')} (sha: {meta.get('content_sha256')})")
    except Exception:
        pass
    try:
        if 'ust_meta' in locals() and ust_meta:
            citations.append(f"UST yields: {ust_meta.get('url')} (sha: {ust_meta.get('content_sha256')})")
    except Exception:
        pass
    try:
        if stooq_meta:
            citations.append(f"Stooq prices: {stooq_meta.get('url')} (sha: {stooq_meta.get('content_sha256')})")
        elif yahoo_meta:
            citations.append(f"Yahoo prices: {yahoo_meta.get('url')} (sha: {yahoo_meta.get('content_sha256')})")
    except Exception:
        pass

    t0 = _time.time()
    md = render_report(I, V, sensitivity_png=heat_png, driver_paths_png=drv_png, citations=citations, fundamentals=(f_for_report if 'f_for_report' in locals() else None))
    eventlog.log(agent="writer_md", outputs={"bytes": len(md.encode('utf-8'))}, duration_ms=int((_time.time()-t0)*1000))
    if last_close is not None:
        md += f"\n\n## Market\n- Last close: {last_close:,.2f}\n- Discount/Premium vs value: {(V.value_per_share/last_close - 1.0):.2%}\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    if cf_json:
        (out_dir / "companyfacts.json").write_text(json.dumps(cf_json))
    (out_dir / "report.md").write_text(md)
    manifest.add_artifact("report.md", md)
    (out_dir / "sensitivity.png").write_bytes(heat_png)
    (out_dir / "drivers.png").write_bytes(drv_png)
    # Also export per-year series CSV
    _write_series_csv(out_dir / "series.csv", I)
    try:
        manifest.add_artifact("series.csv", (out_dir / "series.csv").read_bytes())
    except Exception:
        pass

    if args.html:
        html_text = render_html_report(
            I,
            V,
            sensitivity_png=heat_png,
            driver_paths_png=drv_png,
            fundamentals=(f_for_report if 'f_for_report' in locals() else None),
            companyfacts_json=(cf_for_report if 'cf_for_report' in locals() else None),
        )
        (out_dir / "report.html").write_text(html_text)
        manifest.add_artifact("report.html", html_text)
    # Fundamentals CSV
    if 'f_for_report' in locals() and f_for_report is not None:
        _write_fundamentals_csv(out_dir / "fundamentals.csv", f_for_report)
        try:
            manifest.add_artifact("fundamentals.csv", (out_dir / "fundamentals.csv").read_bytes())
        except Exception:
            pass
    # Write manifest
    manifest.write(out_dir / "manifest.json")
    print(f"Wrote report to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
