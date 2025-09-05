from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Fundamentals(BaseModel):
    company: str
    ticker: str
    currency: str = Field(default="USD")
    asof_date: Optional[date] = None

    # Annual history keyed by year (YYYY)
    revenue: Dict[int, float] = Field(default_factory=dict)
    ebit: Dict[int, float] = Field(default_factory=dict)
    # Optional trailing-twelve-month aggregates (preferred when present)
    revenue_ttm: Optional[float] = None
    ebit_ttm: Optional[float] = None
    tax_rate: Optional[float] = None

    shares_out: Optional[float] = None
    net_debt: Optional[float] = 0.0
    cash_nonop: Optional[float] = 0.0

    sic: Optional[str] = None
