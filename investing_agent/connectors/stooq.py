from __future__ import annotations

import csv
from datetime import datetime
import hashlib
from io import StringIO
from typing import Optional

import requests
from investing_agent.connectors.http_cache import fetch_text as cached_fetch

from investing_agent.schemas.prices import PriceBar, PriceSeries


def _stooq_url_us(ticker: str) -> str:
    # Stooq US tickers use suffix .us
    t = ticker.lower()
    if not t.endswith(".us"):
        t = f"{t}.us"
    return f"https://stooq.com/q/d/l/?s={t}&i=d"


def _parse_prices_text(ticker: str, text: str) -> PriceSeries:
    reader = csv.DictReader(StringIO(text))
    bars = []
    for row in reader:
        try:
            d = datetime.fromisoformat(row["Date"]).date()
            o = float(row["Open"]) if row["Open"] != "-" else None
            h = float(row["High"]) if row["High"] != "-" else None
            l = float(row["Low"]) if row["Low"] != "-" else None
            c = float(row["Close"]) if row["Close"] != "-" else None
            v = float(row["Volume"]) if row.get("Volume") and row["Volume"] != "-" else None
            if None in (o, h, l, c):
                continue
            bars.append(PriceBar(date=d, open=o, high=h, low=l, close=c, volume=v))
        except Exception:
            continue
    return PriceSeries(ticker=ticker.upper(), bars=bars)


def fetch_prices(ticker: str, session: Optional[requests.Session] = None, ttl_seconds: int = 86400) -> PriceSeries:
    url = _stooq_url_us(ticker)
    sess = session or requests.Session()
    text, _meta = cached_fetch(url, ttl_seconds=ttl_seconds, session=sess, timeout=30)
    return _parse_prices_text(ticker, text)


def fetch_prices_with_meta(ticker: str, session: Optional[requests.Session] = None, ttl_seconds: int = 86400) -> tuple[PriceSeries, dict]:
    """
    Fetch Stooq CSV and return (PriceSeries, meta) where meta includes {url, retrieved_at, content_sha256}.
    """
    url = _stooq_url_us(ticker)
    sess = session or requests.Session()
    text, meta_cached = cached_fetch(url, ttl_seconds=ttl_seconds, session=sess, timeout=30)
    ps = _parse_prices_text(ticker, text)
    meta = {
        "url": url,
        "retrieved_at": meta_cached.get("retrieved_at"),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "size": len(text.encode("utf-8")),
        "content_type": "text/csv",
    }
    return ps, meta
