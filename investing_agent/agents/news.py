from __future__ import annotations

"""
News agent (planned)

Searches for recent, valuation-relevant news and ingests it into InputsI via bounded,
schema-checked code updates. LLM may assist with extraction/summarization but must be
deterministic (temp=0, top_p=1, seed=2025) and proposals are validated.
"""

from typing import List, Dict, Any

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def search_news(ticker: str) -> List[Dict[str, Any]]:
    """Search and return a list of news items (placeholder: empty).

    Each item should include at minimum: {"title", "url", "published_at"}.
    """
    # TODO: implement deterministic sources (RSS/APIs) with snapshot logging
    return []


def ingest_and_update(I: InputsI, v: ValuationV, news: List[Dict[str, Any]]) -> InputsI:
    """Apply bounded updates to I based on extracted facts (placeholder: no-op)."""
    # TODO: map extracted facts -> deltas in near-term drivers; clamp; attach provenance
    return I


def summarize(news: List[Dict[str, Any]]) -> str:
    """Return a concise summary of news (placeholder)."""
    # TODO: deterministic template or LLM with deterministic settings
    return ""

