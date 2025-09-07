from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import os
from pathlib import Path

from investing_agent.schemas.research import InsightBundle, InsightCard, InsightQuote
from investing_agent.llm.cassette import replay as cassette_replay, record as cassette_record


ALLOWED_TAGS = {"growth", "margin", "s2c", "wacc", "other"}


def _validate_bundle(bundle: InsightBundle) -> InsightBundle:
    # Enforce: ≥1 quote per card; each quote has snapshot_ids; tags subset of allowed
    cards: List[InsightCard] = []
    for c in bundle.cards:
        if not c.quotes:
            continue
        if any((not q.snapshot_ids) for q in c.quotes):
            continue
        if any((t not in ALLOWED_TAGS) for t in (c.tags or [])):
            # drop unknown tags
            c.tags = [t for t in c.tags if t in ALLOWED_TAGS]
        cards.append(c)
    return InsightBundle(cards=cards)


def _build_request(texts: List[Dict[str, Any]], *, model_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Deterministic request payload; include only minimal needed fields
    compact = []
    for t in texts:
        compact.append({
            "kind": t.get("kind"),
            "snapshot_sha": t.get("snapshot_sha"),
            "url": t.get("url"),
            "date": t.get("date"),
        })
    return {
        "model_id": model_id,
        "params": params,
        "task": "research_summarize_insights",
        "texts": compact,
    }


def generate_insights(
    texts: List[Dict[str, Any]],
    cassette_path: Optional[str] = None,
    *,
    live: bool = False,
    model_id: str = "gpt-4.1-mini",
    params: Dict[str, Any] = {"temperature": 0, "top_p": 1, "seed": 2025},
    cassette_out: Optional[str] = None,
) -> InsightBundle:
    """
    Deterministically create an InsightBundle from cached texts.
    - Replay: if cassette_path (.json) provided, load as InsightBundle
              if cassette_path (.jsonl), replay using request hash
    - Live: gated by flag and CI; records to cassette_out when provided (no real provider call implemented here)
    """
    # Replay JSON cassette directly
    if cassette_path and cassette_path.lower().endswith(".json"):
        data = json.loads(Path(cassette_path).read_text())
        bundle = InsightBundle.model_validate(data)
        return _validate_bundle(bundle)

    req = _build_request(texts, model_id=model_id, params=params)
    # JSONL replay
    if cassette_path and cassette_path.lower().endswith(".jsonl"):
        resp = cassette_replay(req, Path(cassette_path))
        bundle = InsightBundle.model_validate(resp)
        return _validate_bundle(bundle)

    # Live record (no provider implemented here), CI guard
    if live:
        if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
            raise RuntimeError("--insights-llm-live is disabled in CI")
        # Placeholder response: empty bundle (real runs should plug provider)
        resp: Dict[str, Any] = {"cards": []}
        if cassette_out:
            cassette_record(req, resp, Path(cassette_out))
        return InsightBundle(cards=[])

    # Default: empty bundle
    return InsightBundle(cards=[])

