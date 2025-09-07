from __future__ import annotations

import glob
from pathlib import Path

import pytest

from investing_agent.evals.harness import run_case


@pytest.mark.eval
def test_critic_llm_evals():
    base = Path("evals/critic_llm/cases")
    paths = glob.glob(str(base / "*.json"))
    for p in sorted(paths):
        res = run_case(Path(p))
        assert res.passed, f"Eval failed: {res.name}: {res.failures}"

