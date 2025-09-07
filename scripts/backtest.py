#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from investing_agent.schemas.inputs import InputsI
from investing_agent.kernels.ginzu import value as kernel_value


def _load_plan(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"} and yaml is not None:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def _nearest_last_close(prices_csv: Path) -> Optional[float]:
    try:
        rows = list(csv.DictReader(prices_csv.read_text().splitlines()))
        if not rows:
            return None
        last = rows[-1]
        c = last.get("Close") or last.get("close")
        return float(c) if c not in (None, "", "-") else None
    except Exception:
        return None


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Backtest harness (offline, deterministic)")
    ap.add_argument("plan", help="Path to YAML/JSON plan")
    args = ap.parse_args()

    plan = _load_plan(Path(args.plan))
    jobs = plan.get("jobs", [])
    metrics_cfg = plan.get("metrics", {})
    target_mode = metrics_cfg.get("target", "none")

    run_id = os.environ.get("RUN_ID", "backtest")
    out_dir = Path("out") / "_backtests" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    per_rows: List[Dict[str, Any]] = []
    for job in jobs:
        ticker = job.get("ticker")
        if not ticker:
            continue
        base = Path(job.get("base_dir") or (Path("out") / ticker))
        inputs_path = Path(job.get("inputs_path") or (base / "inputs.json"))
        prices_csv = job.get("prices_csv") or (base / "prices.csv")
        asof = job.get("asof")

        try:
            I = InputsI.model_validate_json(Path(inputs_path).read_text())
        except Exception:
            continue
        V = kernel_value(I)
        value_ps = V.value_per_share
        target = None
        if target_mode == "last_close" and Path(prices_csv).exists():
            target = _nearest_last_close(Path(prices_csv))
        abs_err = None
        rel_err = None
        if target and target != 0:
            abs_err = abs(value_ps - target)
            rel_err = abs(value_ps - target) / abs(target)
        per_rows.append({
            "ticker": ticker,
            "asof": asof or (I.asof_date.isoformat() if I.asof_date else ""),
            "value_per_share": f"{value_ps:.6f}",
            "target": f"{target:.6f}" if target is not None else "",
            "abs_err": f"{abs_err:.6f}" if abs_err is not None else "",
            "rel_err": f"{rel_err:.6f}" if rel_err is not None else "",
        })

    # Write per_ticker.csv
    per_path = out_dir / "per_ticker.csv"
    if per_rows:
        with per_path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(per_rows[0].keys()))
            w.writeheader()
            for r in per_rows:
                w.writerow(r)

    # Summary
    abs_errs = [float(r["abs_err"]) for r in per_rows if r.get("abs_err")] 
    rel_errs = [float(r["rel_err"]) for r in per_rows if r.get("rel_err")] 
    summary = {
        "count": len(per_rows),
        "MAD": f"{(sum(abs_errs)/len(abs_errs)):.6f}" if abs_errs else "",
        "MAPE": f"{(sum(rel_errs)/len(rel_errs)):.6f}" if rel_errs else "",
        "median_abs_err": f"{median(abs_errs):.6f}" if abs_errs else "",
    }
    sum_path = out_dir / "summary.csv"
    with sum_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        w.writeheader()
        w.writerow(summary)
    print(f"Wrote backtest to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

