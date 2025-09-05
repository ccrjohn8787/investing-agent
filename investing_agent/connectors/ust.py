from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import Dict, List, Optional

import requests


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
