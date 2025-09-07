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


def build_cmd(job: Dict[str, Any], default_scenario: str | None = None) -> List[str]:
    import sys
    cmd = [sys.executable, "scripts/report.py"]
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
    scen = job.get("scenario") or default_scenario
    if scen:
        cmd.extend(["--scenario", str(scen)])
    # Optional writer + insights flags
    writer = job.get("writer")
    if writer:
        cmd.extend(["--writer", str(writer)])
    wllm = job.get("writer_llm_cassette")
    if wllm:
        cmd.extend(["--writer-llm-cassette", str(wllm)])
    insights = job.get("insights")
    if insights:
        cmd.extend(["--insights", str(insights)])
    return cmd


def main():
    ap = argparse.ArgumentParser(description="Batch runner for reports")
    ap.add_argument("plan", help="YAML/JSON file with jobs and optional defaults")
    ap.add_argument("--run", action="store_true", help="Actually run commands (default: dry-run)")
    args = ap.parse_args()
    plan = load_yaml_or_json(Path(args.plan))
    jobs = plan.get("jobs", [])
    default_scenario = plan.get("scenario")
    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("plan missing jobs list")
    cmds = [build_cmd(job, default_scenario=default_scenario) for job in jobs]
    summary = {"count": len(cmds), "cmds": [" ".join(shlex.quote(c) for c in cmd) for cmd in cmds]}
    print(json.dumps(summary, indent=2))
    if args.run:
        for i, job in enumerate(jobs):
            # Seed inputs.json if provided
            inputs_path = job.get("inputs_path")
            if inputs_path and job.get("ticker"):
                t = str(job.get("ticker")).upper()
                out_dir = Path("out") / t
                out_dir.mkdir(parents=True, exist_ok=True)
                try:
                    Path(inputs_path).replace(out_dir / "inputs.json") if False else None
                except Exception:
                    # Fallback to copy
                    try:
                        (out_dir / "inputs.json").write_text(Path(inputs_path).read_text())
                    except Exception:
                        pass
            subprocess.run(cmds[i], check=False)


if __name__ == "__main__":
    main()
