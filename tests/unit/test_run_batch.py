from __future__ import annotations

import json
from pathlib import Path


def test_run_batch_dry_run(tmp_path: Path):
    plan = {"jobs": [
        {"ticker": "NVDA", "html": True},
        {"ticker": "AAPL", "fresh": True, "growth": "8%,7%"}
    ]}
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))

    import subprocess, sys

    res = subprocess.run([sys.executable, "scripts/run_batch.py", str(p)], capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["count"] == 2
    assert any("NVDA" in cmd for cmd in data["cmds"]) and any("AAPL" in cmd for cmd in data["cmds"]) 

