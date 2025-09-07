#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import InputsI
from investing_agent.agents.writer import render_report


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: write_canary.py <canary_dir>")
        return 2
    base = Path(sys.argv[1])
    inputs_path = base / "inputs.json"
    if not inputs_path.exists():
        print(f"missing {inputs_path}")
        return 2
    I = InputsI.model_validate_json(inputs_path.read_text())
    V = kernel_value(I)
    md = render_report(I, V)
    artifacts = {
        "valuation": sha256_bytes(V.model_dump_json().encode("utf-8")),
        "report.md": sha256_bytes(md.encode("utf-8")),
    }
    # Optional additional artifacts if present in canary folder
    for name in ["series.csv", "fundamentals.csv", "insights.json", "writer_llm.json"]:
        p = base / name
        if p.exists():
            artifacts[name] = sha256_bytes(p.read_bytes())
    out = {"ticker": I.ticker, "artifacts": artifacts}
    (base / "golden.json").write_text(json.dumps(out, indent=2))
    print(f"Wrote golden.json to {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
