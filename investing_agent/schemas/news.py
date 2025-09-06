from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    id: str
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    snippet: Optional[str] = None
    content_sha256: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class NewsBundle(BaseModel):
    ticker: str
    asof: Optional[str] = None
    items: List[NewsItem] = Field(default_factory=list)


class NewsImpact(BaseModel):
    driver: str  # growth | margin | s2c
    start_year_offset: int = 0
    end_year_offset: int = 0
    delta: float
    confidence: float = 0.5
    rationale: Optional[str] = None
    fact_ids: List[str] = Field(default_factory=list)


class NewsSummary(BaseModel):
    facts: List[NewsItem] = Field(default_factory=list)
    impacts: List[NewsImpact] = Field(default_factory=list)
    notes: Optional[str] = None

