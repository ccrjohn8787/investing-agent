#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def load_yaml_or_json(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    if path.suffix.lower() in (".json",):
        return json.loads(text)
    if yaml is None:
        raise SystemExit("YAML not available; install pyyaml or use JSON")
    return yaml.safe_load(text) or {}


def build_cmd(job: Dict[str, Any]) -> List[str]:
    cmd = ["python", "scripts/report.py"]
    ticker = job.get("ticker")
    if not ticker:
        raise ValueError("job missing ticker")
    cmd.append(str(ticker))
    if job.get("fresh"):
        cmd.append("--fresh")
    if job.get("html"):
        cmd.append("--html")
    for key in ("growth", "margin", "s2c", "config"):
        val = job.get(key)
        if val:
            cmd.extend([f"--{key}", str(val)])
    return cmd


def main():
    ap = argparse.ArgumentParser(description="Batch runner for reports")
    ap.add_argument("plan", help="YAML/JSON file with jobs: [{ticker, fresh?, html?, growth?, margin?, s2c?, config?}]")
    ap.add_argument("--run", action="store_true", help="Actually run commands (default: dry-run)")
    args = ap.parse_args()
    plan = load_yaml_or_json(Path(args.plan))
    jobs = plan.get("jobs", [])
    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("plan missing jobs list")
    cmds = [build_cmd(job) for job in jobs]
    summary = {"count": len(cmds), "cmds": [" ".join(shlex.quote(c) for c in cmd) for cmd in cmds]}
    print(json.dumps(summary, indent=2))
    if args.run:
        for cmd in cmds:
            subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()

