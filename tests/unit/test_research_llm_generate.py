from __future__ import annotations

from pathlib import Path

from investing_agent.agents.research_llm import generate_insights


def test_research_llm_replay_bundle_valid():
    cassette = "evals/research_llm/cassettes/sample_insights.json"
    bundle = generate_insights([], cassette_path=cassette)
    assert bundle.cards and len(bundle.cards) >= 2
    for c in bundle.cards:
        assert c.quotes and all(q.snapshot_ids for q in c.quotes)
        assert set(c.tags).issubset({"growth", "margin", "s2c", "wacc", "other"})

