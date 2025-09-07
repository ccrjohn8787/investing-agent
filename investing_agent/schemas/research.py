from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceSpan(BaseModel):
    text: str
    snapshot_sha: Optional[str] = Field(default=None, description="content_sha256 of source snapshot")
    source_url: Optional[str] = None


class InsightCard(BaseModel):
    """
    Contract for research insights used by the LLM Writer.

    - claim: concise statement (no new numbers; may include [ref:...] tokens)
    - quotes: supporting excerpts with provenance
    - snapshot_ids: list of snapshot content hashes referenced
    - tags: topical tags (e.g., mda, product, regulation, accounting)
    - drivers: subset of {growth, margin, s2c, wacc, other}
    - horizon: window over which the claim applies (year offsets)
    - confidence: 0..1 analyst confidence in claim relevance
    - rationale: short glue text linking claim to drivers
    """

    id: str
    claim: str
    quotes: List[EvidenceSpan] = Field(default_factory=list)
    snapshot_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    drivers: List[str] = Field(default_factory=list)
    start_year_offset: int = 0
    end_year_offset: int = 0
    confidence: float = 0.5
    rationale: Optional[str] = None


class InsightBundle(BaseModel):
    ticker: str
    asof: Optional[str] = None
    cards: List[InsightCard] = Field(default_factory=list)

