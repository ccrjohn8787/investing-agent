from __future__ import annotations

"""
Router agent (planned)

Deterministic rule-based router that chooses the next step among
{market, consensus, comparables, sensitivity, news, end} based on simple heuristics
(e.g., recent changes in I/v, availability of new data, critic feedback).

LLM router optional (temp=0, top_p=1, seed=2025) but proposals must flow through
bounded, schema-checked code paths.
"""

from typing import Dict, Tuple


def choose_next(I, v, context: Dict) -> Tuple[str, str | None]:
    """Return (route, instruction). Deterministic placeholder.

    route: one of {"market", "consensus", "comparables", "sensitivity", "news", "end"}
    instruction: optional text, ignored by code unless recognized.
    """
    # TODO: implement deterministic heuristics; for now end immediately
    return "end", None

