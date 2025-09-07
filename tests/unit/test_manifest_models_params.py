from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def test_manifest_models_include_deterministic_params(tmp_path: Path):
    # Seed local inputs to avoid network in report generation
    out_dir = Path("out") / "TST"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Reuse a known valid InputsI from canary to keep test deterministic
    src_inputs = Path("canaries/BYD/inputs.json")
    (out_dir / "inputs.json").write_text(src_inputs.read_text())

    # Provide a local news bundle so --news path engages LLM summarizer with cassette
    news_bundle = {
        "ticker": "TST",
        "asof": "2025-09-03T00:00:00Z",
        "items": [
            {"id": "a", "title": "Guidance raised", "url": "u1", "source": "yahoo", "published_at": "2025-09-02T00:00:00Z"}
        ],
    }
    (out_dir / "news.json").write_text(json.dumps(news_bundle))

    # Run report with cassette-driven writer, research, and news
    args = [
        sys.executable,
        "scripts/report.py",
        "TST",
        "--writer",
        "llm",
        "--writer-llm-cassette",
        "evals/writer_llm/cassettes/coverage_simple.json",
        "--insights-llm-cassette",
        "evals/research_llm/cassettes/sample_insights.json",
        "--news",
        "--news-llm-cassette",
        "evals/news/cassettes/sample_summary.json",
    ]

    import subprocess

    env = os.environ.copy()
    # Avoid live LLM paths in CI
    env["CI"] = "1"
    res = subprocess.run(args, env=env, capture_output=True, text=True)
    assert res.returncode == 0, f"report.py failed: {res.stderr}\n{res.stdout}"

    # Validate manifest models entries include deterministic params
    manifest = json.loads((out_dir / "manifest.json").read_text())
    models = manifest.get("models", {})
    assert "writer" in models and "temp=0;top_p=1;seed=2025" in models["writer"]
    assert "research" in models and "temp=0;top_p=1;seed=2025" in models["research"]
    assert "news" in models and "temp=0;top_p=1;seed=2025" in models["news"]

