from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Optional

import requests
from investing_agent.connectors.http_cache import fetch_text as cached_fetch

from investing_agent.schemas.prices import PriceBar, PriceSeries


def fetch_prices_v8_chart(ticker: str, range_: str = "1y", interval: str = "1d", session: Optional[requests.Session] = None, ttl_seconds: int = 86400) -> PriceSeries:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_}&interval={interval}"
    sess = session or requests.Session()
    text, _meta = cached_fetch(url, ttl_seconds=ttl_seconds, session=sess, timeout=30)
    import json as _json
    data = _json.loads(text)
    result = data.get("chart", {}).get("result", [])
    if not result:
        return PriceSeries(ticker=ticker.upper(), bars=[])
    r0 = result[0]
    ts = r0.get("timestamp", [])
    ind = r0.get("indicators", {}).get("quote", [{}])[0]
    opens = ind.get("open", [])
    highs = ind.get("high", [])
    lows = ind.get("low", [])
    closes = ind.get("close", [])
    vols = ind.get("volume", [])

    bars = []
    for i in range(min(len(ts), len(opens), len(highs), len(lows), len(closes))):
        if None in (opens[i], highs[i], lows[i], closes[i]):
            continue
        d = datetime.fromtimestamp(ts[i], tz=timezone.utc).date()
        bars.append(
            PriceBar(
                date=d,
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=float(vols[i]) if i < len(vols) and vols[i] is not None else None,
            )
        )
    return PriceSeries(ticker=ticker.upper(), bars=bars)


def fetch_prices_v8_chart_with_meta(ticker: str, range_: str = "1y", interval: str = "1d", session: Optional[requests.Session] = None, ttl_seconds: int = 86400) -> tuple[PriceSeries, dict]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_}&interval={interval}"
    sess = session or requests.Session()
    text, meta_cached = cached_fetch(url, ttl_seconds=ttl_seconds, session=sess, timeout=30)
    ps = fetch_prices_v8_chart(ticker, range_=range_, interval=interval, session=sess, ttl_seconds=ttl_seconds)
    meta = {
        "url": url,
        "retrieved_at": meta_cached.get("retrieved_at"),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "size": len(text.encode("utf-8")),
        "content_type": "application/json",
    }
    return ps, meta
