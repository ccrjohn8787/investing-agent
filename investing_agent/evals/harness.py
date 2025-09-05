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


def run_case(path: Path) -> EvalResult:
    case = load_case(path)
    if case.agent == "writer":
        return run_writer_case(case)
    raise NotImplementedError(f"Unsupported agent for eval: {case.agent}")
