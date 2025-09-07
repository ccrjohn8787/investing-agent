#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import glob
from pathlib import Path
from typing import Any, Dict, List

from investing_agent.evals.harness import run_case, load_case


def discover_cases(base: Path) -> List[Path]:
    paths: List[str] = []
    # JSON first
    paths += glob.glob(str(base / "**" / "cases" / "*.json"), recursive=True)
    # YAML optional
    try:
        import yaml  # type: ignore
        _ = yaml  # silence unused
        paths += glob.glob(str(base / "**" / "cases" / "*.yaml"), recursive=True)
        paths += glob.glob(str(base / "**" / "cases" / "*.yml"), recursive=True)
    except Exception:
        pass
    return [Path(p) for p in sorted(paths)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Run eval cases and emit a JSON summary")
    ap.add_argument("--out", default="out/eval_summary.json", help="Output path for summary JSON")
    args = ap.parse_args()

    base = Path("evals")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    counts_by_agent: Dict[str, Dict[str, int]] = {}
    cases = discover_cases(base)
    for p in cases:
        try:
            case = load_case(p)
            res = run_case(p)
            results.append({
                "name": res.name,
                "agent": case.agent,
                "path": str(p),
                "passed": res.passed,
                "failures": res.failures,
                "details": res.details,
            })
            bucket = counts_by_agent.setdefault(case.agent, {"total": 0, "passed": 0, "failed": 0})
            bucket["total"] += 1
            if res.passed:
                bucket["passed"] += 1
            else:
                bucket["failed"] += 1
        except Exception as e:
            results.append({
                "name": p.stem,
                "agent": "unknown",
                "path": str(p),
                "passed": False,
                "failures": [f"exception: {e}"],
                "details": {},
            })
            bucket = counts_by_agent.setdefault("unknown", {"total": 0, "passed": 0, "failed": 0})
            bucket["total"] += 1
            bucket["failed"] += 1

    summary = {
        "total": len(results),
        "by_agent": counts_by_agent,
        "results": results,
    }
    out_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

