from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

from investing_agent.schemas.prices import PriceBar, PriceSeries


def fetch_prices_v8_chart(ticker: str, range_: str = "1y", interval: str = "1d", session: Optional[requests.Session] = None) -> PriceSeries:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_}&interval={interval}"
    sess = session or requests.Session()
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
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

