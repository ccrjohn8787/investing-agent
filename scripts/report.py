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
from investing_agent.agents.market import apply as market_apply
from investing_agent.agents.news import heuristic_summarize, ingest_and_update as news_ingest
from investing_agent.connectors.news import search_news as fetch_news
from investing_agent.schemas.news import NewsBundle, NewsSummary
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
from investing_agent.agents.consensus import apply as consensus_apply
from investing_agent.agents.comparables import apply as comparables_apply


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
    ap.add_argument("--config", help="JSON/YAML file with overrides and settings (growth, margin, s2c, stable_*, beta, discounting, horizon, macro)")
    ap.add_argument("--scenario", help="Scenario name or path (loads configs/scenarios/<name>.yaml if name)")
    ap.add_argument("--consensus", help="Path to consensus JSON (with revenue, ebit arrays)")
    ap.add_argument("--peers", help="Path to peers JSON (list of dicts for comparables)")
    ap.add_argument("--market-target", choices=["none", "last_close"], default="last_close")
    ap.add_argument("--cap-bps", type=float, default=100.0, help="Comparables cap in bps if not set by scenario")
    ap.add_argument("--html", action="store_true", help="Also write HTML report next to Markdown")
    ap.add_argument("--writer", choices=["code", "llm", "hybrid"], default="code", help="Writer mode: code-only, cassette LLM, or hybrid (narrative added)")
    ap.add_argument("--writer-llm-cassette", help="Path to an LLM writer cassette JSON (deterministic narrative)")
    ap.add_argument("--insights", help="Optional path to insights JSON (reserved for future use)")
    ap.add_argument("--news", action="store_true", help="Include News agent (fetch recent RSS and propose impacts)")
    ap.add_argument("--news-window", type=int, default=14, help="News recency window in days")
    ap.add_argument("--news-sources", help="Comma-separated RSS/Atom URLs for news sources (override defaults)")
    ap.add_argument("--news-llm-cassette", help="Path to an LLM cassette JSON to summarize news deterministically")
    ap.add_argument("--filings-limit", type=int, default=0, help="Fetch/cache up to N recent filings (10-K/10-Q/8-K) and record snapshots")
    args = ap.parse_args()
    if not args.ticker:
        raise SystemExit("Provide ticker as arg or set CT/TICKER")

    ticker = args.ticker.upper()
    run_id = _time.strftime("%Y%m%dT%H%M%SZ", _time.gmtime())
    # Load scenario, then config file (config overrides scenario), then CLI overrides
    cfg: dict = {}
    # Scenario load
    if args.scenario:
        scen_arg = args.scenario
        scen_path = Path(scen_arg)
        if not scen_path.exists():
            base = Path("configs/scenarios")
            name = scen_arg if any(scen_arg.endswith(ext) for ext in (".yaml", ".yml")) else f"{scen_arg}.yaml"
            scen_path = base / name
        if scen_path.exists():
            scen_cfg = _load_config(scen_path)
            if isinstance(scen_cfg, dict):
                cfg.update(scen_cfg)
        else:
            print(f"Warning: scenario not found: {scen_arg}")
    # Load config file if provided
    if args.config:
        loaded = _load_config(Path(args.config))
        if isinstance(loaded, dict):
            cfg.update(loaded)

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
    # Record scenario content hash (if any)
    if args.scenario:
        try:
            manifest.add_artifact("scenario", cfg)
        except Exception:
            pass
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

        # Try local cached companyfacts first when not --fresh
        local_cf = out_dir / "companyfacts.json"
        cf_json = None
        if local_cf.exists() and not args.fresh:
            try:
                text = local_cf.read_text()
                cf_json = json.loads(text)
                meta = {
                    "source_url": str(local_cf),
                    "retrieved_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                    "content_sha256": _hashlib.sha256(text.encode("utf-8")).hexdigest(),
                }
                manifest.add_snapshot(Snapshot(source="edgar", url=meta.get("source_url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256")))
            except Exception:
                cf_json = None
        if cf_json is None:
            # Fetch fundamentals
            t0 = _time.time()
            cf_json, meta = fetch_companyfacts(ticker, edgar_ua=edgar_ua)
            eventlog.log(agent="fetch_fundamentals", params={"ticker": ticker}, outputs=meta, duration_ms=int((_time.time()-t0)*1000))
            manifest.add_snapshot(Snapshot(source="edgar", url=meta.get("source_url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256"), size=meta.get("size"), content_type=meta.get("content_type"), license=meta.get("license")))
            # Cache companyfacts
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "companyfacts.json").write_text(json.dumps(cf_json))
            except Exception:
                pass
        f = parse_companyfacts_to_fundamentals(cf_json, ticker=ticker)

        # Macro risk-free from UST latest 10Y with metadata
        # UST: try remote, else local cache out/<TICKER>/ust.csv
        rows, ust_meta = ([], {})
        try:
            rows, ust_meta = fetch_treasury_yield_csv_with_meta()
            manifest.add_snapshot(Snapshot(source="ust", url=ust_meta.get("url"), retrieved_at=ust_meta.get("retrieved_at"), content_sha256=ust_meta.get("content_sha256"), size=ust_meta.get("size"), content_type=ust_meta.get("content_type")))
            # Cache CSV
            try:
                (out_dir / "ust.csv").write_text("\n".join([",".join(r.keys())] + [",".join(r.values()) for r in rows]) if rows else "")
            except Exception:
                pass
        except Exception:
            pass
        if not rows:
            # Try local cache
            p = out_dir / "ust.csv"
            if p.exists():
                try:
                    import csv
                    from io import StringIO
                    text = p.read_text()
                    reader = csv.DictReader(StringIO(text))
                    rows = [r for r in reader]
                    ust_meta = {"url": str(p), "retrieved_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()), "content_sha256": _hashlib.sha256(text.encode("utf-8")).hexdigest()}
                    manifest.add_snapshot(Snapshot(source="ust", url=ust_meta.get("url"), retrieved_at=ust_meta.get("retrieved_at"), content_sha256=ust_meta.get("content_sha256")))
                except Exception:
                    rows = []
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
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "inputs.json").write_text(I.model_dump_json(indent=2))
        except Exception:
            pass

    # Optional transforms from consensus/peers prior to initial valuation
    if args.consensus:
        p = Path(args.consensus)
        try:
            text = p.read_text()
            data = json.loads(text)
            I = consensus_apply(I, consensus_data=data)
            manifest.add_snapshot(
                Snapshot(
                    source="consensus",
                    url=str(p),
                    retrieved_at=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                    content_sha256=_hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
        except Exception as e:
            print(f"Warning: failed to apply consensus from {p}: {e}")
    if args.peers:
        p = Path(args.peers)
        try:
            text = p.read_text()
            peers = json.loads(text)
            comp_cfg = cfg.get("comparables", {}) if isinstance(cfg.get("comparables"), dict) else {}
            cap_bps = float(comp_cfg.get("cap_bps", float(args.cap_bps)))
            I = comparables_apply(I, peers=peers, policy={"cap_bps": cap_bps})
            manifest.add_snapshot(
                Snapshot(
                    source="peers",
                    url=str(p),
                    retrieved_at=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                    content_sha256=_hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
        except Exception as e:
            print(f"Warning: failed to apply peers from {p}: {e}")

    t0 = _time.time()
    V = kernel_value(I)
    eventlog.log(agent="valuation", inputs=I.model_dump(), outputs=V.model_dump(), duration_ms=int((_time.time()-t0)*1000))
    manifest.add_artifact("valuation", V.model_dump())
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "valuation.json").write_text(V.model_dump_json(indent=2))
    except Exception:
        pass

    # Try prices via Stooq; fallback to Yahoo, and degrade gracefully offline.
    # Parallelize price fetching and sensitivity computation to reduce wall time.
    from investing_agent.schemas.prices import PriceSeries
    stooq_meta = None
    yahoo_meta = None
    def _fetch_prices() -> tuple[PriceSeries, Optional[dict], Optional[dict]]:
        try:
            t0 = _time.time()
            p, meta_s = fetch_prices_stooq_with_meta(ticker)
            eventlog.log(agent="prices", params={"source": "stooq"}, outputs={"bars": len(p.bars)}, duration_ms=int((_time.time()-t0)*1000))
            return p, meta_s, None
        except Exception:
            try:
                t0 = _time.time()
                p, meta_y = fetch_prices_v8_chart_with_meta(ticker)
                eventlog.log(agent="prices", params={"source": "yahoo"}, outputs={"bars": len(p.bars)}, duration_ms=int((_time.time()-t0)*1000))
                return p, None, meta_y
            except Exception:
                return PriceSeries(ticker=ticker, bars=[]), None, None

    # Launch price fetch concurrently
    ps = None
    try:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_prices = ex.submit(_fetch_prices)
            # Compute sensitivity while fetching prices
            t0 = _time.time()
            sens = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(5, 5))
            heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {ticker}")
            eventlog.log(agent="sensitivity", params={"steps": (5,5)}, outputs={"grid": [len(sens.margin_axis), len(sens.growth_axis)]}, duration_ms=int((_time.time()-t0)*1000))
            ps, stooq_meta, yahoo_meta = fut_prices.result()
    except Exception:
        # Fallback to sequential if threadpool not available or errors occurred
        try:
            t0 = _time.time()
            ps, stooq_meta = fetch_prices_stooq_with_meta(ticker)
            eventlog.log(agent="prices", params={"source": "stooq"}, outputs={"bars": len(ps.bars)}, duration_ms=int((_time.time()-t0)*1000))
        except Exception:
            try:
                t0 = _time.time()
                ps, yahoo_meta = fetch_prices_v8_chart_with_meta(ticker)
                eventlog.log(agent="prices", params={"source": "yahoo"}, outputs={"bars": len(ps.bars)}, duration_ms=int((_time.time()-t0)*1000))
            except Exception:
                ps = PriceSeries(ticker=ticker, bars=[])
        # Sensitivity sequential (if not done)
        t0 = _time.time()
        sens = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(5, 5))
        heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {ticker}")
        eventlog.log(agent="sensitivity", params={"steps": (5,5)}, outputs={"grid": [len(sens.margin_axis), len(sens.growth_axis)]}, duration_ms=int((_time.time()-t0)*1000))
    # Local fallback: out/<TICKER>/prices.csv (Stooq format)
    if not ps.bars:
        try:
            p = out_dir / "prices.csv"
            if p.exists():
                import csv
                from datetime import datetime
                rows = list(csv.DictReader(p.open()))
                bars = []
                from investing_agent.schemas.prices import PriceBar
                for row in rows:
                    try:
                        d = datetime.fromisoformat(row["Date"]).date()
                        o = float(row["Open"]) if row.get("Open") not in (None, "-") else None
                        h = float(row["High"]) if row.get("High") not in (None, "-") else None
                        l = float(row["Low"]) if row.get("Low") not in (None, "-") else None
                        c = float(row["Close"]) if row.get("Close") not in (None, "-") else None
                        v = float(row["Volume"]) if row.get("Volume") not in (None, "-") else None
                        if None in (o, h, l, c):
                            continue
                        bars.append(PriceBar(date=d, open=o, high=h, low=l, close=c, volume=v))
                    except Exception:
                        continue
                ps = PriceSeries(ticker=ticker, bars=bars)
                manifest.add_snapshot(Snapshot(source="prices_csv", url=str(p), retrieved_at=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()), content_sha256=_hashlib.sha256(p.read_bytes()).hexdigest()))
        except Exception:
            pass
    last_close = ps.bars[-1].close if ps.bars else None

    # Record price feed snapshot
    try:
        if stooq_meta:
            manifest.add_snapshot(Snapshot(source="stooq", url=stooq_meta.get("url"), retrieved_at=stooq_meta.get("retrieved_at"), content_sha256=stooq_meta.get("content_sha256"), size=stooq_meta.get("size"), content_type=stooq_meta.get("content_type")))
        elif yahoo_meta:
            manifest.add_snapshot(Snapshot(source="yahoo", url=yahoo_meta.get("url"), retrieved_at=yahoo_meta.get("retrieved_at"), content_sha256=yahoo_meta.get("content_sha256"), size=yahoo_meta.get("size"), content_type=yahoo_meta.get("content_type")))
    except Exception:
        pass

    import numpy as np
    from investing_agent.agents.plotting import plot_pv_bridge, plot_price_vs_value

    g = np.array(I.drivers.sales_growth)
    m = np.array(I.drivers.oper_margin)
    w = np.array(I.wacc)
    drv_png = plot_driver_paths(len(g), g, m, w)
    bridge_png = plot_pv_bridge(V)
    price_png = None
    try:
        if ps and ps.bars:
            price_png = plot_price_vs_value(ps, V.value_per_share, title=f"Price vs Value — {ticker}")
    except Exception:
        price_png = None

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
    try:
        if args.consensus:
            citations.append(f"Consensus: {args.consensus}")
    except Exception:
        pass
    try:
        if args.peers:
            citations.append(f"Peers: {args.peers}")
    except Exception:
        pass

    # Optional: market solver (scenario-gated) to reconcile intrinsic value with market cap
    try:
        enable_market = bool(cfg.get("router", {}).get("enable_market", False))
        if args.market_target == "last_close" and enable_market and last_close is not None and last_close > 0 and I.shares_out > 0:
            ms_cfg = cfg.get("market_solver", {}) if isinstance(cfg.get("market_solver"), dict) else {}
            steps_cfg = ms_cfg.get("steps") or (5, 5, 5)
            I2 = market_apply(
                I,
                target_value_per_share=float(last_close),
                weights=ms_cfg.get("weights"),
                bounds=ms_cfg.get("bounds"),
                steps=tuple(steps_cfg) if isinstance(steps_cfg, (list, tuple)) else (5, 5, 5),
            )
            if I2 != I:
                I = I2
                t1 = _time.time()
                V = kernel_value(I)
                eventlog.log(agent="market_solve", params={"target_vps": last_close}, inputs=cfg.get("market_solver"), outputs={"value_per_share": V.value_per_share}, duration_ms=int((_time.time()-t1)*1000))
                manifest.add_artifact("post_market_inputs", I.model_dump())
                manifest.add_artifact("post_market_valuation", V.model_dump())
                # Recompute sensitivity on adjusted inputs
                sens = compute_sensitivity(I, growth_delta=0.02, margin_delta=0.01, steps=(5, 5))
                heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {ticker}")
                g = np.array(I.drivers.sales_growth)
                m = np.array(I.drivers.oper_margin)
                w = np.array(I.wacc)
                drv_png = plot_driver_paths(len(g), g, m, w)
                bridge_png = plot_pv_bridge(V)
                try:
                    if ps and ps.bars:
                        price_png = plot_price_vs_value(ps, V.value_per_share, title=f"Price vs Value — {ticker}")
                except Exception:
                    price_png = None
    except Exception:
        pass

    # Optional: News agent pipeline (offline-first)
    news_summary: NewsSummary | None = None
    if args.news:
        # Try local bundle first
        news_bundle: NewsBundle | None = None
        local_news = out_dir / "news.json"
        if local_news.exists() and not args.fresh:
            try:
                news_bundle = NewsBundle.model_validate_json(local_news.read_text())
            except Exception:
                news_bundle = None
        if news_bundle is None:
            try:
                # Sources from CLI or scenario
                sources_arg = args.news_sources
                srcs = None
                if not sources_arg:
                    scen_news = cfg.get("news") if isinstance(cfg.get("news"), dict) else {}
                    scen_srcs = scen_news.get("sources") if isinstance(scen_news, dict) else None
                    if isinstance(scen_srcs, list) and scen_srcs:
                        srcs = [(f"src{i+1}", url) for i, url in enumerate(scen_srcs)]
                else:
                    urls = [u.strip() for u in sources_arg.split(",") if u.strip()]
                    srcs = [(f"src{i+1}", url) for i, url in enumerate(urls)]
                nb, metas = fetch_news(ticker, window_days=int(args.news_window), sources=srcs)
                news_bundle = nb
                (out_dir / "news.json").write_text(nb.model_dump_json(indent=2))
                # Record snapshots for sources
                try:
                    for meta in metas:
                        manifest.add_snapshot(Snapshot(source="news", url=meta.get("url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256")))
                except Exception:
                    pass
            except Exception:
                news_bundle = None
        if news_bundle and news_bundle.items:
            if args.news_llm_cassette:
                from investing_agent.agents.news import llm_summarize
                news_summary = llm_summarize(news_bundle, I, scenario=cfg, cassette_path=args.news_llm_cassette)
                # Record model id used in manifest
                manifest.models["news"] = "gpt-4.1-mini@deterministic:cassette"
            else:
                news_summary = heuristic_summarize(news_bundle, I, scenario=cfg)
            I = news_ingest(I, V, news_summary, scenario=cfg)
            V = kernel_value(I)  # update valuation after ingestion
            bridge_png = plot_pv_bridge(V)
            manifest.add_artifact("news.json", news_bundle.model_dump())
            manifest.add_artifact("news_summary.json", news_summary.model_dump())

    # LLM writer cassette (optional)
    writer_llm_out = None
    if args.writer in ("llm", "hybrid") and args.writer_llm_cassette:
        try:
            from investing_agent.schemas.writer_llm import WriterLLMOutput
            text = Path(args.writer_llm_cassette).read_text()
            data = json.loads(text)
            writer_llm_out = WriterLLMOutput.model_validate(data)
            # Record model in manifest if cassette metadata provided
            model_meta = None
            try:
                model_meta = writer_llm_out.metadata or {}
            except Exception:
                model_meta = None
            if model_meta:
                model_id = model_meta.get("model") or model_meta.get("model_id")
                params = model_meta.get("params")
                if model_id and params:
                    manifest.models["writer"] = f"{model_id}@cassette"
                elif model_id:
                    manifest.models["writer"] = str(model_id)
                else:
                    manifest.models["writer"] = "writer-llm@cassette"
        except Exception:
            writer_llm_out = None

    t0 = _time.time()
    md = render_report(
        I,
        V,
        sensitivity_png=heat_png,
        driver_paths_png=drv_png,
        citations=citations,
        fundamentals=(f_for_report if 'f_for_report' in locals() else None),
        pv_bridge_png=bridge_png,
        price_vs_value_png=price_png,
        news=news_summary,
        llm_output=writer_llm_out,
    )
    # Scenario section (if provided)
    if args.scenario:
        md += "\n\n## Scenario\n"
        md += f"- Scenario: {args.scenario}\n"
        # surface key builder-related items if present
        for k in ["horizon", "discounting", "stable_growth", "stable_margin", "beta"]:
            if k in cfg:
                md += f"- {k}: {cfg[k]}\n"
    eventlog.log(agent="writer_md", outputs={"bytes": len(md.encode('utf-8'))}, duration_ms=int((_time.time()-t0)*1000))
    if last_close is not None:
        md += f"\n\n## Market\n- Last close: {last_close:,.2f}\n- Discount/Premium vs value: {(V.value_per_share/last_close - 1.0):.2%}\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    if cf_json:
        (out_dir / "companyfacts.json").write_text(json.dumps(cf_json))
    (out_dir / "report.md").write_text(md)
    manifest.add_artifact("report.md", md)
    # Optional filings fetch/cache (evidence corpus; snapshot only)
    try:
        if int(args.filings_limit) > 0:
            from investing_agent.connectors.filings import fetch_filings_index, fetch_filing_text, extract_text, cache_and_snapshot
            idx = fetch_filings_index(ticker, types=["10-K", "10-Q", "8-K"], limit=int(args.filings_limit))
            for row in idx:
                url = row.get("url") if isinstance(row, dict) else None
                typ = (row.get("type") if isinstance(row, dict) else None) or "filing"
                if not url:
                    continue
                text, _meta = fetch_filing_text(url)
                # Normalize/extract
                kind = "10-K" if "10-K" in typ else ("10-Q" if "10-Q" in typ else "8-K")
                norm = extract_text(text, kind=kind)
                cache_and_snapshot(ticker, typ, url, norm, manifest)
    except Exception:
        pass
    (out_dir / "sensitivity.png").write_bytes(heat_png)
    (out_dir / "drivers.png").write_bytes(drv_png)
    (out_dir / "pv_bridge.png").write_bytes(bridge_png)
    if price_png:
        (out_dir / "price_vs_value.png").write_bytes(price_png)
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
            pv_bridge_png=bridge_png,
            price_vs_value_png=price_png,
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
