#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import csv
import hashlib

import numpy as np

from investing_agent.agents.comparables import apply as comparables_apply
from investing_agent.agents.consensus import apply as consensus_apply
from investing_agent.agents.market import apply as market_apply
from investing_agent.agents.plotting import plot_driver_paths, plot_sensitivity_heatmap, plot_pv_bridge, plot_price_vs_value
from investing_agent.agents.router import choose_next
from investing_agent.agents.critic import check_report
from investing_agent.agents.sensitivity import compute_sensitivity
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.agents.writer import render_report
from investing_agent.agents.news import heuristic_summarize, ingest_and_update as news_ingest, llm_summarize
from investing_agent.connectors.news import search_news as fetch_news
from investing_agent.schemas.news import NewsBundle, NewsSummary
from investing_agent.connectors import ust as ust_mod
from investing_agent.connectors.edgar import (
    fetch_companyfacts,
    parse_companyfacts_to_fundamentals,
)
from investing_agent.connectors.stooq import fetch_prices_with_meta as fetch_prices_stooq_with_meta
from investing_agent.connectors.yahoo import fetch_prices_v8_chart_with_meta
from investing_agent.connectors.ust import (
    build_risk_free_curve_from_ust,
    fetch_treasury_yield_csv_with_meta,
)
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.orchestration.eventlog import EventLog
from investing_agent.orchestration.manifest import Manifest, Snapshot
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.schemas.inputs import InputsI


def _load_json(path: Optional[str]) -> Optional[dict | list]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _rel_delta(curr: float, prev: Optional[float]) -> Optional[float]:
    if prev is None or prev == 0:
        return None
    return abs(curr - prev) / abs(prev)


def _update_convergence_state(ctx: Dict[str, Any], prev_vps: Optional[float], curr_vps: float, *, threshold: float, steps_break: int) -> None:
    """Update ctx with within-threshold steps count and recent sensitivity flag management."""
    rd = _rel_delta(curr_vps, prev_vps)
    if rd is not None and rd <= threshold:
        ctx["within_threshold_steps"] = int(ctx.get("within_threshold_steps", 0)) + 1
    else:
        ctx["within_threshold_steps"] = 0


def _should_end(ctx: Dict[str, Any], critic_issues: list[str], last_admitted_news_big: bool, *, steps_break: int) -> bool:
    if int(ctx.get("within_threshold_steps", 0)) >= int(steps_break) and not critic_issues and not last_admitted_news_big:
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Supervisor CLI: orchestrate valuation with router loop")
    ap.add_argument("ticker", nargs="?", default=os.environ.get("CT") or os.environ.get("TICKER"))
    ap.add_argument("--fresh", action="store_true", help="Bypass cached inputs and fetch live fundamentals")
    ap.add_argument("--consensus", help="Path to consensus JSON (revenue_y1/y2, ebit_y1/y2)")
    ap.add_argument("--peers", help="Path to peers JSON (list with stable_margin, etc.)")
    ap.add_argument("--market-target", choices=["last_close", "none"], default="none")
    ap.add_argument("--cap-bps", type=float, default=100.0, help="Cap for market and comparables (bps)")
    ap.add_argument("--max-iters", type=int, default=8)
    ap.add_argument("--html", action="store_true", help="Also write HTML report")
    ap.add_argument("--scenario", help="Scenario name or path (loads configs/scenarios/<name>.yaml if name)")
    ap.add_argument("--offline", action="store_true", help="Offline mode: use cached/local files; no network")
    ap.add_argument("--inputs-json", help="Path to cached inputs.json to use directly (skips EDGAR/UST)")
    ap.add_argument("--companyfacts-json", help="Path to local EDGAR companyfacts JSON (default: out/<TICKER>/companyfacts.json)")
    ap.add_argument("--ust-csv", help="Path to local UST CSV (Treasury yield curve)")
    ap.add_argument("--prices-csv", help="Path to local prices CSV (Stooq format: Date,Open,High,Low,Close,Volume)")
    ap.add_argument("--news-window", type=int, default=14, help="News recency window in days")
    ap.add_argument("--news-sources", help="Comma-separated RSS/Atom URLs for news sources (override defaults)")
    ap.add_argument("--news-llm-cassette", help="Path to an LLM cassette JSON to summarize news deterministically")
    ap.add_argument("--critic-llm-cassette", help="Path to an LLM critic cassette JSON (deterministic)")
    args = ap.parse_args()
    if not args.ticker:
        raise SystemExit("Provide ticker as arg or set CT/TICKER")

    ticker = args.ticker.upper()
    out_dir = Path("out") / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    eventlog = EventLog(out_dir / "run.jsonl")
    manifest = Manifest(run_id=os.environ.get("RUN_ID", "supervisor"), ticker=ticker)

    # Scenario config
    def _load_config(path: Path) -> dict:
        try:
            text = path.read_text()
        except Exception:
            return {}
        try:
            import yaml  # type: ignore

            return yaml.safe_load(text) or {}
        except Exception:
            try:
                return json.loads(text)
            except Exception:
                return {}

    cfg: dict = {}
    if args.scenario:
        scen = args.scenario
        p = Path(scen)
        if not p.exists():
            base = Path("configs/scenarios")
            name = scen if any(scen.endswith(ext) for ext in (".yaml", ".yml")) else f"{scen}.yaml"
            p = base / name
        if p.exists():
            cfg.update(_load_config(p))

    # Fetch or load fundamentals
    if args.inputs_json:
        # Use direct cached inputs
        I: InputsI = InputsI.model_validate_json(Path(args.inputs_json).read_text())
        f = Fundamentals(company=I.company, ticker=I.ticker, currency=I.currency)
        cf_json = {}
        meta = {"source_url": "local:inputs", "retrieved_at": datetime.utcnow().isoformat() + "Z", "content_sha256": None}
    else:
        if args.offline:
            local_cf = Path(args.companyfacts_json) if args.companyfacts_json else (out_dir / "companyfacts.json")
            if not local_cf.exists():
                raise SystemExit(f"Offline mode: missing {local_cf}")
            text = local_cf.read_text()
            cf_json = json.loads(text)
            meta = {
                "source_url": str(local_cf),
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
                "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            f = parse_companyfacts_to_fundamentals(cf_json, ticker=ticker)
            manifest.add_snapshot(Snapshot(source="edgar", url=meta.get("source_url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256")))
        else:
            edgar_ua = os.environ.get("EDGAR_UA")
            if not edgar_ua:
                print("Warning: EDGAR_UA not set; SEC requests may be blocked.")
            cf_json, meta = fetch_companyfacts(ticker, edgar_ua=edgar_ua)
            f = parse_companyfacts_to_fundamentals(cf_json, ticker=ticker)
            manifest.add_snapshot(Snapshot(source="edgar", url=meta.get("source_url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256")))

    # Macro risk-free via UST
    def _load_local_ust_csv(path: Path) -> Tuple[list[dict], dict]:
        text = path.read_text()
        rdr = csv.DictReader(text.splitlines())
        rows = [r for r in rdr]
        meta = {"url": str(path), "retrieved_at": datetime.utcnow().isoformat() + "Z", "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        return rows, meta

    if args.inputs_json:
        # keep existing rf in inputs; no UST needed
        rf_curve = I.macro.risk_free_curve or [0.03] * 10
        ust_meta = None
    elif args.offline and args.ust_csv:
        rows, ust_meta = _load_local_ust_csv(Path(args.ust_csv))
        manifest.add_snapshot(Snapshot(source="ust", url=ust_meta.get("url"), retrieved_at=ust_meta.get("retrieved_at"), content_sha256=ust_meta.get("content_sha256")))
        rf_curve = build_risk_free_curve_from_ust(rows, horizon=10)
    elif args.offline:
        rf_curve = [0.03] * 10
        ust_meta = None
    else:
        rows, ust_meta = fetch_treasury_yield_csv_with_meta()
        manifest.add_snapshot(Snapshot(source="ust", url=ust_meta.get("url"), retrieved_at=ust_meta.get("retrieved_at"), content_sha256=ust_meta.get("content_sha256")))
        rf_curve = build_risk_free_curve_from_ust(rows, horizon=10)

    # Build inputs
    from investing_agent.schemas.inputs import Macro

    macro = Macro(risk_free_curve=rf_curve, erp=0.05, country_risk=0.0)
    if not args.inputs_json:
        I: InputsI = build_inputs_from_fundamentals(f, horizon=10, macro=macro)
    # Set EDGAR provenance into inputs for report
    I.provenance.vendor = "SEC EDGAR"
    I.provenance.source_url = meta.get("source_url")
    I.provenance.retrieved_at = meta.get("retrieved_at")
    I.provenance.content_sha256 = meta.get("content_sha256")
    manifest.add_artifact("inputs", I.model_dump())

    V = kernel_value(I)
    manifest.add_artifact("valuation", V.model_dump())

    # Prices
    last_close = None
    stooq_meta = None
    yahoo_meta = None
    if args.offline and args.prices_csv:
        from investing_agent.schemas.prices import PriceSeries, PriceBar

        p = Path(args.prices_csv)
        text = p.read_text()
        rdr = csv.DictReader(text.splitlines())
        bars = []
        for row in rdr:
            try:
                d = datetime.fromisoformat(row["Date"]).date()
                o = float(row["Open"]) if row["Open"] != "-" else None
                h = float(row["High"]) if row["High"] != "-" else None
                l = float(row["Low"]) if row["Low"] != "-" else None
                c = float(row["Close"]) if row["Close"] != "-" else None
            except Exception:
                continue
            if None in (o, h, l, c):
                continue
            vol = float(row.get("Volume", 0)) if row.get("Volume") and row.get("Volume") != "-" else None
            bars.append(PriceBar(date=d, open=o, high=h, low=l, close=c, volume=vol))
        ps = PriceSeries(ticker=ticker.upper(), bars=bars)
        last_close = ps.bars[-1].close if ps.bars else None
        meta_prices = {"url": str(p), "retrieved_at": datetime.utcnow().isoformat() + "Z", "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        manifest.add_snapshot(Snapshot(source="prices_csv", url=meta_prices.get("url"), retrieved_at=meta_prices.get("retrieved_at"), content_sha256=meta_prices.get("content_sha256")))
    elif args.offline:
        # No prices available; skip market-last_close route
        last_close = None
    else:
        try:
            ps, stooq_meta = fetch_prices_stooq_with_meta(ticker)
            last_close = ps.bars[-1].close if ps.bars else None
            manifest.add_snapshot(Snapshot(source="stooq", url=stooq_meta.get("url"), retrieved_at=stooq_meta.get("retrieved_at"), content_sha256=stooq_meta.get("content_sha256")))
        except Exception:
            ps, yahoo_meta = fetch_prices_v8_chart_with_meta(ticker)
            last_close = ps.bars[-1].close if ps.bars else None
            manifest.add_snapshot(Snapshot(source="yahoo", url=yahoo_meta.get("url"), retrieved_at=yahoo_meta.get("retrieved_at"), content_sha256=yahoo_meta.get("content_sha256")))

    # Optional data inputs
    consensus_data = _load_json(args.consensus)
    peers = _load_json(args.peers)
    # Record snapshots for local consensus/peers if provided
    if args.consensus:
        p = Path(args.consensus)
        if p.exists():
            try:
                text = p.read_text()
                manifest.add_snapshot(Snapshot(source="consensus", url=str(p), retrieved_at=datetime.utcnow().isoformat() + "Z", content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest()))
            except Exception:
                pass
    if args.peers:
        p = Path(args.peers)
        if p.exists():
            try:
                text = p.read_text()
                manifest.add_snapshot(Snapshot(source="peers", url=str(p), retrieved_at=datetime.utcnow().isoformat() + "Z", content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest()))
            except Exception:
                pass

    # Router context
    router_cfg = cfg.get("router", {}) if isinstance(cfg.get("router"), dict) else {}
    ctx: Dict[str, Any] = {
        "iter": 0,
        "max_iters": int(args.max_iters),
        "last_value": None,
        "unchanged_steps": 0,
        "ran_sensitivity_recent": False,
        "within_threshold_steps": 0,
        "have_consensus": bool(consensus_data) and bool(router_cfg.get("enable_consensus", False)),
        "have_comparables": bool(peers) and bool(router_cfg.get("enable_comparables", False)),
        "allow_news": bool(router_cfg.get("enable_news", False)),
        "last_route": None,
    }

    # Loop
    heat_png = None
    drv_png = None
    delta_value_threshold = float(router_cfg.get("delta_value_threshold", 0.005))
    unchanged_steps_break = int(router_cfg.get("unchanged_steps_break", 2))
    last_admitted_news_big = False

    while True:
        # Convergence gate: if we are within threshold for required steps and have no blockers, stop
        # Compute critic issues on-demand (cheap)
        critic_issues: list[str] = []
        try:
            tmp_md = render_report(I, V)
            critic_issues = check_report(tmp_md, I, V, manifest=manifest)
        except Exception:
            critic_issues = []
        # Optional LLM critic (cassette-based)
        llm_error_block = False
        try:
            router_llm = bool(router_cfg.get("enable_llm_critic", False))
            if router_llm and args.critic_llm_cassette:
                from investing_agent.agents.critic_llm import check as check_llm
                llm_issues = check_llm(tmp_md, I, V, cassette_path=args.critic_llm_cassette)
                # Log model id used
                manifest.models["critic"] = "gpt-4.1-mini@deterministic:cassette"
                # Any error severity is a blocker
                llm_error_block = any(str(x).lower().startswith("error:") for x in llm_issues)
        except Exception:
            llm_error_block = False
        if _should_end(ctx, critic_issues, last_admitted_news_big, steps_break=unchanged_steps_break) and not llm_error_block:
            break
        route, _ = choose_next(I, V, ctx)
        if route == "end":
            break
        prev_v = V.value_per_share
        if route == "market":
            if args.market_target == "last_close" and last_close and bool(router_cfg.get("enable_market", True)):
                ms_cfg = cfg.get("market_solver", {}) if isinstance(cfg.get("market_solver"), dict) else {}
                steps_cfg = ms_cfg.get("steps") or (5, 5, 5)
                I = market_apply(
                    I,
                    target_value_per_share=float(last_close),
                    weights=ms_cfg.get("weights"),
                    bounds=ms_cfg.get("bounds"),
                    steps=tuple(steps_cfg) if isinstance(steps_cfg, (list, tuple)) else (5, 5, 5),
                )
                V = kernel_value(I)
        elif route == "consensus" and consensus_data:
            I = consensus_apply(I, consensus_data=consensus_data)
            V = kernel_value(I)
        elif route == "comparables" and isinstance(peers, list):
            comp_cfg = cfg.get("comparables", {}) if isinstance(cfg.get("comparables"), dict) else {}
            cap_bps = float(comp_cfg.get("cap_bps", float(args.cap_bps)))
            I = comparables_apply(I, peers=peers, policy={"cap_bps": cap_bps})
            V = kernel_value(I)
        elif route == "news" and bool(router_cfg.get("enable_news", False)):
            # News agent step (offline-first)
            news_bundle: NewsBundle | None = None
            local_news = out_dir / "news.json"
            if local_news.exists() and args.offline:
                try:
                    news_bundle = NewsBundle.model_validate_json(local_news.read_text())
                except Exception:
                    news_bundle = None
            if news_bundle is None and not args.offline:
                try:
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
                    for meta in metas:
                        try:
                            manifest.add_snapshot(Snapshot(source="news", url=meta.get("url"), retrieved_at=meta.get("retrieved_at"), content_sha256=meta.get("content_sha256")))
                        except Exception:
                            pass
                except Exception:
                    news_bundle = None
            if news_bundle and news_bundle.items:
                if args.news_llm_cassette:
                    summary = llm_summarize(news_bundle, I, scenario=cfg, cassette_path=args.news_llm_cassette)
                    manifest.models["news"] = "gpt-4.1-mini@deterministic:cassette"
                else:
                    summary = heuristic_summarize(news_bundle, I, scenario=cfg)
                # Track whether any newly admitted impact is >= 1% (absolute)
                last_admitted_news_big = any(abs(getattr(imp, "delta", 0.0)) >= 0.01 for imp in (summary.impacts or []))
                I = news_ingest(I, V, summary, scenario=cfg)
                V = kernel_value(I)
                try:
                    (out_dir / "news_summary.json").write_text(summary.model_dump_json(indent=2))
                except Exception:
                    pass
        elif route == "sensitivity":
            sens = compute_sensitivity(I)
            heat_png = plot_sensitivity_heatmap(sens, title=f"Sensitivity — {I.ticker}")
            g = np.array(I.drivers.sales_growth)
            m = np.array(I.drivers.oper_margin)
            w = np.array(I.wacc)
            drv_png = plot_driver_paths(len(g), g, m, w)
            ctx["ran_sensitivity_recent"] = True
        else:
            # Non-news step resets the flag for gating of new admissions
            last_admitted_news_big = False
        # Update loop state
        ctx["iter"] += 1
        ctx["last_route"] = route
        ctx["unchanged_steps"] = ctx.get("unchanged_steps", 0) + 1 if prev_v == V.value_per_share else 0
        # Update convergence counters using relative delta threshold
        _update_convergence_state(ctx, prev_v, V.value_per_share, threshold=delta_value_threshold, steps_break=unchanged_steps_break)
        ctx["last_value"] = prev_v

    # Build charts
    bridge_png = plot_pv_bridge(V)
    price_png = None
    try:
        if last_close is not None and ps and ps.bars:
            price_png = plot_price_vs_value(ps, V.value_per_share, title=f"Price vs Value — {ticker}")
    except Exception:
        price_png = None

    # Citations
    citations: list[str] = []
    citations.append(f"EDGAR companyfacts: {meta.get('source_url')} (sha: {meta.get('content_sha256')})")
    if ust_meta:
        citations.append(f"UST yields: {ust_meta.get('url')} (sha: {ust_meta.get('content_sha256')})")
    if stooq_meta:
        citations.append(f"Stooq prices: {stooq_meta.get('url')} (sha: {stooq_meta.get('content_sha256')})")
    elif yahoo_meta:
        citations.append(f"Yahoo prices: {yahoo_meta.get('url')} (sha: {yahoo_meta.get('content_sha256')})")
    if args.consensus:
        citations.append(f"Consensus: {args.consensus}")
    if args.peers:
        citations.append(f"Peers: {args.peers}")

    # Render report
    md = render_report(I, V, sensitivity_png=heat_png, driver_paths_png=drv_png, citations=citations, fundamentals=f, pv_bridge_png=bridge_png, price_vs_value_png=price_png)
    (out_dir / "report.md").write_text(md)
    if args.html:
        from investing_agent.agents.html_writer import render_html_report

        html = render_html_report(I, V, sensitivity_png=heat_png, driver_paths_png=drv_png, fundamentals=f, companyfacts_json=cf_json, pv_bridge_png=bridge_png, price_vs_value_png=price_png)
        (out_dir / "report.html").write_text(html)

    # Save plots
    if heat_png:
        (out_dir / "sensitivity.png").write_bytes(heat_png)
    if drv_png:
        (out_dir / "drivers.png").write_bytes(drv_png)
    (out_dir / "pv_bridge.png").write_bytes(bridge_png)
    if price_png:
        (out_dir / "price_vs_value.png").write_bytes(price_png)

    # Record scenario in manifest if provided
    if args.scenario:
        try:
            manifest.add_artifact("scenario", cfg)
        except Exception:
            pass
    manifest.add_artifact("report.md", md)
    manifest.write(out_dir / "manifest.json")
    print(f"Supervisor wrote report to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
