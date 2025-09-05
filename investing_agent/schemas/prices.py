from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class PriceBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class PriceSeries(BaseModel):
    ticker: str
    bars: List[PriceBar] = Field(default_factory=list)

