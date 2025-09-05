from __future__ import annotations

import glob
from pathlib import Path

import pytest

from investing_agent.evals.harness import run_case


@pytest.mark.eval
def test_writer_eval_cases_pass():
    base = Path("evals/writer/cases")
    try:
        import yaml  # type: ignore
        yaml_paths = glob.glob(str(base / "*.yaml"))
    except Exception:
        yaml_paths = []
    for path in sorted(yaml_paths + glob.glob(str(base / "*.json"))):
        res = run_case(Path(path))
        assert res.passed, f"Eval failed: {res.name}: {res.failures}"
