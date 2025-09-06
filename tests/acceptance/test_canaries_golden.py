from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import pytest

from investing_agent.agents.critic import check_report
from investing_agent.agents.writer import render_report
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.schemas.inputs import InputsI


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.mark.acceptance
def test_canary_golden_hashes():
    for canary_dir in sorted(glob.glob("canaries/*")):
        base = Path(canary_dir)
        ipath = base / "inputs.json"
        gpath = base / "golden.json"
        if not ipath.exists() or not gpath.exists():
            pytest.skip(f"missing inputs or golden in {base}")
        I = InputsI.model_validate_json(ipath.read_text())
        V = kernel_value(I)
        md = render_report(I, V)
        issues = check_report(md, I, V)
        assert issues == [], f"Critic issues for {base}: {issues}"
        golden = load_json(gpath)
        expected = golden.get("artifacts", {})
        actual = {
            "valuation": sha256_bytes(V.model_dump_json().encode("utf-8")),
            "report.md": sha256_bytes(md.encode("utf-8")),
        }
        assert actual == expected, f"Golden mismatch for {base}: {actual} vs {expected}"

