from __future__ import annotations

import csv
from datetime import datetime
import hashlib
from io import StringIO
from typing import Dict, List, Optional

import requests
from investing_agent.connectors.http_cache import fetch_text as cached_fetch


TREASURY_YIELD_CSV = (
    "https://home.treasury.gov/sites/default/files/interest-rates/yield.csv"
)
TREASURY_YIELD_FALLBACKS = [
    # Common alternates used by Treasury site
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv",
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/datasets/yield.csv",
]


def fetch_treasury_yield_csv(url: str = TREASURY_YIELD_CSV, session: Optional[requests.Session] = None) -> List[dict]:
    """
    Fetch the Treasury par yield curve CSV and return rows as dicts.
    The standard CSV has columns: Date, 1 Mo, 2 Mo, 3 Mo, 6 Mo, 1 Yr, 2 Yr, 3 Yr, 5 Yr, 7 Yr, 10 Yr, 20 Yr, 30 Yr.
    """
    sess = session or requests.Session()
    urls = [url] + TREASURY_YIELD_FALLBACKS
    last_err: Optional[Exception] = None
    for u in urls:
        try:
            resp = sess.get(u, timeout=30)
            resp.raise_for_status()
            text = resp.text
            reader = csv.DictReader(StringIO(text))
            rows = [r for r in reader]
            if rows:
                return rows
        except Exception as e:
            last_err = e
            continue
    # If all attempts fail, return empty list; downstream uses defaults
    return []


def fetch_treasury_yield_csv_with_meta(url: str = TREASURY_YIELD_CSV, session: Optional[requests.Session] = None, ttl_seconds: int = 86400) -> tuple[List[dict], dict]:
    """
    Like fetch_treasury_yield_csv, but also returns a meta dict with {url, retrieved_at, content_sha256}.
    On failure, returns ([], {url, retrieved_at, content_sha256: None}).
    """
    sess = session or requests.Session()
    urls = [url] + TREASURY_YIELD_FALLBACKS
    for u in urls:
        try:
            text, meta_cached = cached_fetch(u, ttl_seconds=ttl_seconds, session=sess, timeout=30)
            reader = csv.DictReader(StringIO(text))
            rows = [r for r in reader]
            meta = {
                "url": u,
                "retrieved_at": meta_cached.get("retrieved_at"),
                "content_sha256": meta_cached.get("content_sha256"),
                "size": len(text.encode("utf-8")),
                "content_type": "text/csv",
            }
            return rows, meta
        except Exception:
            continue
    return [], {"url": url, "retrieved_at": datetime.utcnow().isoformat() + "Z", "content_sha256": None, "size": None, "content_type": None}


def latest_yield_curve(rows: List[dict]) -> Dict[str, float]:
    if not rows:
        return {}
    last = rows[-1]
    curve: Dict[str, float] = {}
    for k, v in last.items():
        kk = k.strip().lower()
        if kk == "date":
            continue
        try:
            curve[kk] = float(v) / 100.0  # convert percent to decimal
        except Exception:
            continue
    return curve


def build_risk_free_curve_from_ust(rows: List[dict], horizon: int) -> List[float]:
    curve = latest_yield_curve(rows)
    # Prefer 10 yr; fallback to 5 yr; else average available
    r10 = curve.get("10 yr") or curve.get("10yr") or curve.get("10yr.")
    if r10 is None:
        r10 = curve.get("5 yr") or curve.get("5yr")
    if r10 is None and curve:
        r10 = sum(curve.values()) / len(curve)
    if r10 is None:
        r10 = 0.03
    return [float(r10)] * horizon
