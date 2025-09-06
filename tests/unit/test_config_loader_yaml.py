from __future__ import annotations

import json
import pytest


def test_load_config_yaml(tmp_path):
    yaml = pytest.importorskip("yaml")
    data = {
        "horizon": 11,
        "discounting": "midyear",
        "beta": 1.2,
        "growth": ["8%", "7%"],
        "margin": [0.12, 0.13],
        "s2c": [2.0, 2.1],
        "macro": {"risk_free_curve": [0.05] * 11, "erp": 0.055, "country_risk": 0.01},
    }
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(data))

    from scripts.report import _load_config

    cfg = _load_config(p)
    assert cfg["horizon"] == 11
    assert cfg["discounting"] == "midyear"
    assert cfg["growth"] == ["8%", "7%"]
    assert cfg["macro"]["erp"] == pytest.approx(0.055)

