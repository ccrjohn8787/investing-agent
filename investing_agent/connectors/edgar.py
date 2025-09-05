from __future__ import annotations

import hashlib
import time
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple, List

import requests

from investing_agent.schemas.fundamentals import Fundamentals


SEC_BASE = "https://data.sec.gov"
SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"


def _ua_headers(edgar_ua: Optional[str]) -> Dict[str, str]:
    ua = edgar_ua or "email@example.com Investing-Agent/0.1"
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ensure_cik10(cik: str | int) -> str:
    s = "".join(ch for ch in str(cik) if ch.isdigit())
    s = s.lstrip("0") or "0"
    return f"CIK{s.zfill(10)}"


def _load_ticker_map(edgar_ua: Optional[str] = None, session: Optional[requests.Session] = None) -> Dict[str, int]:
    """
    Load SEC ticker->CIK map. Returns dict of TICKER (upper) -> CIK (int).
    Endpoint format is a JSON object keyed by string indices, each value like
    {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}.
    """
    sess = session or requests.Session()
    resp = sess.get(SEC_TICKER_MAP_URL, headers=_ua_headers(edgar_ua), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    mapping: Dict[str, int] = {}
    # Accept either dict-of-dicts (indexed) or list
    if isinstance(data, dict):
        it = data.values()
    elif isinstance(data, list):
        it = data
    else:
        it = []
    for row in it:
        try:
            t = str(row.get("ticker", "")).upper().strip()
            cik = int(row.get("cik_str"))
        except Exception:
            continue
        if t:
            mapping[t] = cik
    return mapping


def _resolve_cik10(cik_or_ticker: str, edgar_ua: Optional[str] = None, session: Optional[requests.Session] = None) -> str:
    """Resolve input (CIK digits or TICKER) to zero-padded CIK########## string with CIK prefix."""
    s = str(cik_or_ticker).strip()
    if s.isdigit():
        return _ensure_cik10(s)
    # Treat as ticker; load mapping
    mapping = _load_ticker_map(edgar_ua=edgar_ua, session=session)
    cik = mapping.get(s.upper())
    if not cik:
        raise ValueError(f"Unknown ticker for SEC mapping: {cik_or_ticker}")
    return _ensure_cik10(cik)


def fetch_companyfacts(cik_or_ticker: str, edgar_ua: Optional[str] = None, session: Optional[requests.Session] = None) -> Tuple[dict, dict]:
    """
    Fetch SEC companyfacts JSON for a CIK or a ticker. Returns (json, meta) where meta includes
    {source_url, retrieved_at, content_sha256}.
    Note: Requires network and a valid SEC User-Agent string.
    """
    sess = session or requests.Session()
    cik10 = _resolve_cik10(cik_or_ticker, edgar_ua=edgar_ua, session=sess)
    url = f"{SEC_BASE}/api/xbrl/companyfacts/{cik10}.json"
    headers = _ua_headers(edgar_ua)
    resp = sess.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    b = resp.content
    meta = {
        "source_url": url,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "content_sha256": _hash_bytes(b),
        "license": "SEC public data",
    }
    return resp.json(), meta


def _pick_fact_unit(fact: dict, unit_priority: Iterable[str]) -> Optional[dict]:
    units: dict = fact.get("units", {})
    for u in unit_priority:
        if u in units and units[u]:
            return {"unit": u, "series": units[u]}
    return None

def _scale_for_unit(unit: str) -> float:
    unit = (unit or "").lower().strip()
    if unit == "usd":
        return 1.0
    if unit == "usdm":
        return 1_000_000.0
    if unit in ("usdth", "usd000"):  # thousands
        return 1_000.0
    # Default: no scale
    return 1.0


def _to_annual(series: Iterable[dict], scale: float = 1.0) -> Dict[int, float]:
    ann: Dict[int, float] = {}
    for item in series:
        try:
            fy = item.get("fy")
            fp = item.get("fp")
            val = float(item.get("val")) * float(scale)
        except Exception:
            continue
        if not fy or fp not in ("FY", "Q4", "FYR"):
            # Prefer full-year; many facts have only FY
            pass
        end = item.get("end")
        year = None
        if fy:
            try:
                year = int(fy)
            except Exception:
                year = None
        if year is None and end:
            try:
                year = datetime.fromisoformat(end).year
            except Exception:
                continue
        if year is None:
            continue
        # Keep latest filing per year
        if year not in ann:
            ann[year] = val
        else:
            ann[year] = val
    return ann


def _quarter_of_fp(fp: Optional[str]) -> Optional[int]:
    if not fp:
        return None
    fp = str(fp).upper().strip()
    if fp.startswith("Q1"):
        return 1
    if fp.startswith("Q2"):
        return 2
    if fp.startswith("Q3"):
        return 3
    if fp.startswith("Q4"):
        return 4
    return None


def _collect_quarters(series: Iterable[dict], scale: float = 1.0) -> List[tuple]:
    qrows: List[tuple] = []
    for item in series:
        try:
            fy = int(item.get("fy")) if item.get("fy") is not None else None
            fp = item.get("fp")
            q = _quarter_of_fp(fp)
            end = item.get("end")
            val = float(item.get("val")) * float(scale)
        except Exception:
            continue
        if q is None:
            continue
        try:
            end_dt = datetime.fromisoformat(end).date() if end else None
        except Exception:
            end_dt = None
        if end_dt is None:
            # fallback: synthesize by year/quarter order
            end_dt = datetime(int(fy) if fy else 1900, max(1, q * 3), 1).date()
        qrows.append((end_dt, fy, q, val))
    qrows.sort(key=lambda x: x[0])
    return qrows


def _ttm_from_quarters(series: Iterable[dict], scale: float = 1.0) -> Optional[float]:
    qs = _collect_quarters(series, scale=scale)
    if len(qs) < 4:
        return None
    # Sum last 4 quarters
    last_four = [v for (_, _, _, v) in qs[-4:]]
    return float(sum(last_four))


REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
]
EBIT_TAGS = [
    "OperatingIncomeLoss",
]
SHARES_TAGS = [
    "CommonStockSharesOutstanding",
]
TAX_RATE_TAGS = [
    "EffectiveIncomeTaxRateContinuingOperations",
    "EffectiveIncomeTaxRate",
]


def parse_companyfacts_to_fundamentals(cf: dict, ticker: str, company: Optional[str] = None) -> Fundamentals:
    facts = cf.get("facts", {}).get("us-gaap", {})
    # Revenue
    revenue = {}
    revenue_ttm: Optional[float] = None
    for tag in REVENUE_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                series = pick["series"]
                revenue = _to_annual(series, scale=scale)
                # Try TTM from quarters
                ttm = _ttm_from_quarters(series, scale=scale)
                if ttm and ttm > 0:
                    revenue_ttm = ttm
                if revenue:
                    break

    # If TTM not found yet, try other tags for quarterly series without overriding annual dict
    if revenue_ttm is None:
        for tag in REVENUE_TAGS:
            if tag in facts:
                pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
                if not pick:
                    continue
                scale = _scale_for_unit(pick["unit"])
                ttm = _ttm_from_quarters(pick["series"], scale=scale)
                if ttm and ttm > 0:
                    revenue_ttm = ttm
                    break

    # EBIT
    ebit = {}
    ebit_ttm: Optional[float] = None
    for tag in EBIT_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["USD", "USDm", "USDth"])
            if pick:
                scale = _scale_for_unit(pick["unit"])
                series = pick["series"]
                ebit = _to_annual(series, scale=scale)
                # Try TTM
                ttm = _ttm_from_quarters(series, scale=scale)
                if ttm and ttm > 0:
                    ebit_ttm = ttm
                if ebit:
                    break

    # Shares
    shares_out = None
    for tag in SHARES_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["shares"])
            if pick and pick["series"]:
                ann = _to_annual(pick["series"], scale=1.0)
                if ann:
                    # Use the latest year
                    y = max(ann.keys())
                    shares_out = float(ann[y])
                    break

    # Tax rate (approximate)
    tax_rate = None
    for tag in TAX_RATE_TAGS:
        if tag in facts:
            pick = _pick_fact_unit(facts[tag], ["pure"])
            if pick and pick["series"]:
                ann = _to_annual(pick["series"], scale=1.0)
                if ann:
                    y = max(ann.keys())
                    tr = float(ann[y])
                    if tr > 1:
                        tr = tr / 100.0
                    tax_rate = max(0.0, min(0.6, tr))
                    break

    return Fundamentals(
        company=company or cf.get("entityName", ticker),
        ticker=ticker,
        currency="USD",
        revenue=revenue,
        ebit=ebit,
        revenue_ttm=revenue_ttm,
        ebit_ttm=ebit_ttm,
        shares_out=shares_out,
        tax_rate=tax_rate,
    )
