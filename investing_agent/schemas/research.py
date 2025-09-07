from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class InsightQuote(BaseModel):
    text: str
    snapshot_ids: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class InsightCard(BaseModel):
    claim: str
    tags: List[str] = Field(default_factory=list)
    start_year_offset: int = 0
    end_year_offset: int = 0
    confidence: float = 0.5
    quotes: List[InsightQuote] = Field(default_factory=list)


class InsightBundle(BaseModel):
    cards: List[InsightCard] = Field(default_factory=list)

