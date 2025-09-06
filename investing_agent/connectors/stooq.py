from __future__ import annotations

import csv
from datetime import datetime
import hashlib
from io import StringIO
from typing import Optional

import requests

from investing_agent.schemas.prices import PriceBar, PriceSeries


def _stooq_url_us(ticker: str) -> str:
    # Stooq US tickers use suffix .us
    t = ticker.lower()
    if not t.endswith(".us"):
        t = f"{t}.us"
    return f"https://stooq.com/q/d/l/?s={t}&i=d"


def fetch_prices(ticker: str, session: Optional[requests.Session] = None) -> PriceSeries:
    url = _stooq_url_us(ticker)
    sess = session or requests.Session()
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
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


def fetch_prices_with_meta(ticker: str, session: Optional[requests.Session] = None) -> tuple[PriceSeries, dict]:
    """
    Fetch Stooq CSV and return (PriceSeries, meta) where meta includes {url, retrieved_at, content_sha256}.
    """
    url = _stooq_url_us(ticker)
    sess = session or requests.Session()
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
    ps = fetch_prices(ticker, session=sess)
    meta = {
        "url": url,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    return ps, meta
