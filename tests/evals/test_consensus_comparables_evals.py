from __future__ import annotations

import glob
from pathlib import Path

import pytest

from investing_agent.evals.harness import run_case


@pytest.mark.eval
def test_consensus_evals():
    base = Path("evals/consensus/cases")
    paths = glob.glob(str(base / "*.json"))
    for p in sorted(paths):
        res = run_case(Path(p))
        assert res.passed, f"Eval failed: {res.name}: {res.failures}"


@pytest.mark.eval
@pytest.mark.xfail(reason="comparables not implemented yet; eval-first contracts only", strict=False)
def test_comparables_evals():
    base = Path("evals/comparables/cases")
    paths = glob.glob(str(base / "*.json"))
    for p in sorted(paths):
        res = run_case(Path(p))
        assert res.passed, f"Eval failed: {res.name}: {res.failures}"
