from __future__ import annotations

from pathlib import Path


def test_backtest_outputs_tmp(tmp_path, monkeypatch):
    # Copy fixtures to tmp and run backtest
    base = tmp_path / "bt"
    (base / "BT1").mkdir(parents=True, exist_ok=True)
    src = Path("tests/fixtures/backtest/BT1")
    (base / "BT1" / "inputs.json").write_text((src / "inputs.json").read_text())
    (base / "BT1" / "prices.csv").write_text((src / "prices.csv").read_text())
    plan = tmp_path / "plan.json"
    plan.write_text('{"jobs": [{"ticker": "BT1", "base_dir": "%s"}], "metrics": {"target": "last_close"}}' % str(base / "BT1").replace('\\', '/'))

    import subprocess, sys
    out = subprocess.run([sys.executable, "scripts/backtest.py", str(plan)], capture_output=True, text=True)
    assert out.returncode == 0
    # Check outputs
    run_dir = Path("out/_backtests/backtest")
    assert (run_dir / "per_ticker.csv").exists()
    assert (run_dir / "summary.csv").exists()
    # Summary has non-empty metrics
    txt = (run_dir / "summary.csv").read_text()
    assert "count" in txt

