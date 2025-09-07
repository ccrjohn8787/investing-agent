from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import json
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

from investing_agent.agents.writer import render_report
from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.fundamentals import Fundamentals
from investing_agent.agents.consensus import apply as consensus_apply
from investing_agent.agents.comparables import apply as comparables_apply
from investing_agent.agents.market import apply as market_apply
from investing_agent.agents.news import heuristic_summarize
from investing_agent.schemas.news import NewsBundle


@dataclass
class EvalCase:
    name: str
    agent: str
    params: Dict[str, Any]
    checks: Dict[str, Any]


@dataclass
class EvalResult:
    name: str
    passed: bool
    failures: List[str]
    details: Dict[str, Any]


def load_case(path: Path) -> EvalCase:
    text = path.read_text()
    if path.suffix.lower() in {".json"}:
        data = json.loads(text)
    else:
        if yaml is None:
            raise RuntimeError("PyYAML not installed; use JSON eval cases or install pyyaml")
        data = yaml.safe_load(text)
    return EvalCase(
        name=data.get("name") or path.stem,
        agent=data["agent"],
        params=data.get("params", {}),
        checks=data.get("checks", {}),
    )


def run_writer_case(case: EvalCase) -> EvalResult:
    p = case.params
    f = Fundamentals(
        company=p.get("company", "EvalCo"),
        ticker=p.get("ticker", "EVAL"),
        currency=p.get("currency", "USD"),
        revenue=p.get("revenue", {}),
        ebit=p.get("ebit", {}),
        shares_out=float(p.get("shares_out", 1000.0)),
        tax_rate=float(p.get("tax_rate", 0.25)),
    )
    horizon = int(p.get("horizon", 5))
    I = build_inputs_from_fundamentals(f, horizon=horizon)
    V = kernel_value(I)
    md = render_report(I, V)

    failures: List[str] = []
    checks = case.checks or {}
    for s in checks.get("contains", []) or []:
        if s not in md:
            failures.append(f"missing substring: {s!r}")
    for s in checks.get("not_contains", []) or []:
        if s in md:
            failures.append(f"unexpected substring present: {s!r}")

    return EvalResult(
        name=case.name,
        passed=len(failures) == 0,
        failures=failures,
        details={"len_md": len(md)},
    )


def run_consensus_case(case: EvalCase) -> EvalResult:
    p = case.params
    # Base fundamentals and consensus inputs
    rev0 = float(p.get("revenue_t0", 1000.0))
    rev1 = float(p.get("consensus", {}).get("revenue_y1", 1100.0))
    rev2 = float(p.get("consensus", {}).get("revenue_y2", 1210.0))
    ebit1 = float(p.get("consensus", {}).get("ebit_y1", 150.0))
    ebit2 = float(p.get("consensus", {}).get("ebit_y2", 170.0))
    f = Fundamentals(
        company=p.get("company", "EvalCo"),
        ticker=p.get("ticker", "EVAL"),
        currency=p.get("currency", "USD"),
        revenue={2023: rev0},
        ebit={2023: float(p.get("ebit_t0", 120.0))},
        shares_out=float(p.get("shares_out", 1000.0)),
        tax_rate=float(p.get("tax_rate", 0.25)),
    )
    horizon = int(p.get("horizon", 6))
    I = build_inputs_from_fundamentals(f, horizon=horizon)
    # Allow full consensus payload passthrough if present; otherwise build from y1/y2 fields
    consensus_payload = dict(p.get("consensus", {}))
    has_direct = any(k in consensus_payload for k in ("growth", "margin", "revenue", "ebit", "smoothing", "smooth_to_stable", "bounds"))
    if has_direct:
        consensus_data = consensus_payload
        used_mapping_from_rev = False
    else:
        consensus_data = {"revenue": [rev1, rev2], "ebit": [ebit1, ebit2]}
        used_mapping_from_rev = True

    J = consensus_apply(I, consensus_data)

    # Expected mapping: g1=(rev1-rev0)/rev0; g2=(rev2-rev1)/rev1; m1=ebit1/rev1; m2=ebit2/rev2
    exp_g1 = (rev1 - rev0) / rev0 if rev0 else 0.0
    exp_g2 = (rev2 - rev1) / rev1 if rev1 else 0.0
    exp_m1 = (ebit1 / rev1) if rev1 else 0.0
    exp_m2 = (ebit2 / rev2) if rev2 else 0.0

    tol = float(case.checks.get("tol", 1e-6))
    failures: List[str] = []
    if used_mapping_from_rev:
        try:
            if abs(J.drivers.sales_growth[0] - exp_g1) > tol:
                failures.append(f"g1 mismatch: got {J.drivers.sales_growth[0]:.6f}, exp {exp_g1:.6f}")
            if abs(J.drivers.sales_growth[1] - exp_g2) > tol:
                failures.append(f"g2 mismatch: got {J.drivers.sales_growth[1]:.6f}, exp {exp_g2:.6f}")
            if abs(J.drivers.oper_margin[0] - exp_m1) > tol:
                failures.append(f"m1 mismatch: got {J.drivers.oper_margin[0]:.6f}, exp {exp_m1:.6f}")
            if abs(J.drivers.oper_margin[1] - exp_m2) > tol:
                failures.append(f"m2 mismatch: got {J.drivers.oper_margin[1]:.6f}, exp {exp_m2:.6f}")
        except Exception as e:
            failures.append(f"exception during checks: {e}")

    # Optional smoothing check: tail values trend to stable
    if case.checks.get("tail_to_stable"):
        try:
            if abs(J.drivers.sales_growth[-1] - J.drivers.stable_growth) > tol:
                failures.append("tail growth not close to stable")
            if abs(J.drivers.oper_margin[-1] - J.drivers.stable_margin) > tol:
                failures.append("tail margin not close to stable")
        except Exception as e:
            failures.append(f"exception during tail check: {e}")

    return EvalResult(name=case.name, passed=len(failures) == 0, failures=failures, details={})


def run_comparables_case(case: EvalCase) -> EvalResult:
    p = case.params
    f = Fundamentals(
        company=p.get("company", "EvalCo"),
        ticker=p.get("ticker", "EVAL"),
        currency=p.get("currency", "USD"),
        revenue={2023: float(p.get("revenue_t0", 1000.0))},
        ebit={2023: float(p.get("ebit_t0", 120.0))},
        shares_out=float(p.get("shares_out", 1000.0)),
        tax_rate=float(p.get("tax_rate", 0.25)),
    )
    horizon = int(p.get("horizon", 6))
    I = build_inputs_from_fundamentals(f, horizon=horizon)
    # Apply base stable margin if provided
    if "stable_margin" in p:
        I.drivers.stable_margin = float(p["stable_margin"])
    peers = p.get("peers", [])
    policy = p.get("policy", {"cap_bps": 100})
    J = comparables_apply(I, peers=peers, policy=policy)

    # Expected: move stable margin toward median by at most cap
    cap = float(policy.get("cap_bps", 100)) / 10000.0
    if peers:
        sm0 = float(I.drivers.stable_margin)
        med = sorted([float(x["stable_margin"]) for x in peers])[len(peers)//2]
        gap = med - sm0
        exp = sm0 + max(-cap, min(cap, gap))
    else:
        exp = float(I.drivers.stable_margin)

    tol = float(case.checks.get("tol", 1e-6))
    failures: List[str] = []
    try:
        if abs(J.drivers.stable_margin - exp) > tol:
            failures.append(f"stable_margin mismatch: got {J.drivers.stable_margin:.6f}, exp {exp:.6f}")
    except Exception as e:
        failures.append(f"exception during checks: {e}")

    return EvalResult(name=case.name, passed=len(failures) == 0, failures=failures, details={})


def run_market_case(case: EvalCase) -> EvalResult:
    p = case.params
    f = Fundamentals(
        company=p.get("company", "EvalCo"),
        ticker=p.get("ticker", "EVAL"),
        currency=p.get("currency", "USD"),
        revenue={2023: float(p.get("revenue_t0", 1000.0))},
        ebit={2023: float(p.get("ebit_t0", 120.0))},
        shares_out=float(p.get("shares_out", 1000.0)),
        tax_rate=float(p.get("tax_rate", 0.25)),
    )
    horizon = int(p.get("horizon", 6))
    I = build_inputs_from_fundamentals(f, horizon=horizon)
    # Optional override base stable margin
    if "stable_margin" in p:
        I.drivers.stable_margin = float(p["stable_margin"])
    cap_bps = float(p.get("cap_bps", 100))
    target_mode = p.get("target_mode")
    if target_mode == "sm_cap":
        # Compute target as valuation with stable margin moved by cap in given direction
        direction = p.get("direction", "up")
        cap = cap_bps / 10000.0
        sm0 = float(I.drivers.stable_margin)
        sm_target = sm0 + (cap if direction == "up" else -cap)
        sm_target = max(0.05, min(0.35, sm_target))
        K = I.model_copy(deep=True)
        K.drivers.stable_margin = sm_target
        target_price = kernel_value(K).value_per_share
    else:
        target_price = float(p.get("target_price", 0.0))

    J = market_apply(I, context={"target_price": target_price, "cap_bps": cap_bps})
    Vj = kernel_value(J)
    tol = float(case.checks.get("tol", 1e-6))
    failures: List[str] = []
    # Check relative error to target
    if target_price != 0:
        rel = abs(Vj.value_per_share - target_price) / abs(target_price)
        if rel > tol:
            failures.append(f"target mismatch: got {Vj.value_per_share:.6f}, target {target_price:.6f}")
    # Check stable margin moved no more than cap
    cap = cap_bps / 10000.0
    if abs(J.drivers.stable_margin - I.drivers.stable_margin) - cap > 1e-9:
        failures.append("stable_margin moved beyond cap")
    return EvalResult(name=case.name, passed=len(failures) == 0, failures=failures, details={})


def run_case(path: Path) -> EvalResult:
    case = load_case(path)
    if case.agent == "writer":
        return run_writer_case(case)
    if case.agent == "consensus":
        return run_consensus_case(case)
    if case.agent == "comparables":
        return run_comparables_case(case)
    if case.agent == "market":
        return run_market_case(case)
    if case.agent == "news":
        return run_news_case(case)
    raise NotImplementedError(f"Unsupported agent for eval: {case.agent}")


def run_news_case(case: EvalCase) -> EvalResult:
    p = case.params
    caps = p.get("caps") or {"growth_bps": 50, "margin_bps": 30}
    bundle = NewsBundle.model_validate(p.get("bundle") or {"ticker": "EVAL", "items": []})
    # Use heuristic summarizer (no LLM in CI)
    from investing_agent.schemas.inputs import InputsI, Drivers
    I = InputsI(
        company="EvalCo",
        ticker=bundle.ticker,
        currency="USD",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        drivers=Drivers(sales_growth=[0.05]*6, oper_margin=[0.15]*6, stable_growth=0.02, stable_margin=0.15),
        sales_to_capital=[2.0]*6,
        wacc=[0.06]*6,
    )
    mode = (case.params.get("mode") or "heuristic").lower()
    if mode == "llm":
        cassette = case.params.get("cassette")
        from investing_agent.agents.news import llm_summarize
        summary = llm_summarize(bundle, I, scenario={"news": {"caps": caps}}, cassette_path=cassette)
    else:
        summary = heuristic_summarize(bundle, I, scenario={"news": {"caps": caps}})
    failures: List[str] = []
    if case.checks.get("min_impacts", 0) > 0 and len(summary.impacts) < int(case.checks["min_impacts"]):
        failures.append("insufficient impacts")
    # Bounds check: deltas must be within caps
    cap_g = float(caps.get("growth_bps", 50))/10000.0
    cap_m = float(caps.get("margin_bps", 30))/10000.0
    for imp in summary.impacts:
        if imp.driver == "growth" and abs(imp.delta) - cap_g > 1e-9:
            failures.append("growth delta exceeds cap")
        if imp.driver == "margin" and abs(imp.delta) - cap_m > 1e-9:
            failures.append("margin delta exceeds cap")
        if not imp.fact_ids:
            failures.append("impact missing fact_ids")
    return EvalResult(name=case.name, passed=len(failures)==0, failures=failures, details={"impacts": len(summary.impacts)})
