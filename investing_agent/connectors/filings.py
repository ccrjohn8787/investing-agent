from __future__ import annotations

"""
Filings connector (deterministic, no LLM)

Functions:
- fetch_filings_index(ticker, types, limit): return a deterministic list of filings metadata
- fetch_filing_text(url, ttl_seconds): fetch/cached text via http_cache
- extract_text(html_or_text, kind): strip HTML and select likely MD&A/body; normalize deterministically

Also provides a helper to cache text to out/<TICKER>/filings and record a Manifest snapshot.
"""

import hashlib
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from investing_agent.connectors.http_cache import fetch_text as cached_fetch_text, fetch_json as cached_fetch_json
from investing_agent.orchestration.manifest import Manifest, Snapshot


def _norm_text(s: str) -> str:
    # Normalize to ASCII, collapse whitespace deterministically
    s2 = s.encode("ascii", errors="ignore").decode("ascii")
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2


def _strip_html(html: str) -> str:
    # Remove scripts/styles
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    # Extract body if present
    m = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, flags=re.IGNORECASE)
    body = m.group(1) if m else html
    # Drop tags
    text = re.sub(r"<[^>]+>", " ", body)
    return text


def extract_text(html_or_text: str, kind: str) -> str:
    """Extract deterministic text from HTML or plain text.

    kind: "10-K"|"10-Q"|"8-K" informs selection heuristics.
    - For 10-K/10-Q, try to isolate MD&A if present.
    - For 8-K, extract body text.
    Returns normalized ASCII text with collapsed whitespace.
    """
    s = html_or_text or ""
    looks_html = "<" in s and "/>" in s or "</" in s
    txt = _strip_html(s) if looks_html else s
    lower = txt.lower()
    start = 0
    end = len(txt)
    if kind in ("10-K", "10-Q"):
        # MD&A anchors
        anchors = [
            "management's discussion and analysis",
            "managements discussion and analysis",
            "management discussion and analysis",
        ]
        # End anchors
        ends = [
            "item 7a",  # K
            "item 8",
            "financial statements",
        ]
        for a in anchors:
            i = lower.find(a)
            if i != -1:
                start = i
                break
        # Find nearest plausible end after start
        if start > 0:
            lo = lower[start:]
            cand_idx: List[int] = []
            for e in ends:
                j = lo.find(e)
                if j != -1:
                    cand_idx.append(start + j)
            if cand_idx:
                end = min(cand_idx)
    elif kind == "8-K":
        # Use entire body already stripped
        pass
    chunk = txt[start:end]
    return _norm_text(chunk)


def fetch_filings_index(ticker: str, types: List[str], limit: int = 8) -> List[Dict[str, str]]:
    """Fetch a filings index for a ticker and return a deterministic list of rows.

    Expected item shape per row: {"type": ..., "date": "YYYY-MM-DD", "url": ..., "title": optional}
    Deterministic order: date desc, then url asc. Truncated to `limit`.
    Tests monkeypatch `cached_fetch_json` to return local fixtures; live network not required here.
    """
    # Placeholder URL — tests patch fetch_json, so the exact URL is irrelevant
    url = f"https://example.sec/filings/{ticker}.json"
    data, _meta = cached_fetch_json(url, ttl_seconds=86400)
    items: List[Dict[str, Any]]
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        items = list(data["items"])  # type: ignore[assignment]
    elif isinstance(data, list):
        items = data  # type: ignore[assignment]
    else:
        items = []
    # Filter by type if provided
    want = {t.upper() for t in types or []}
    out: List[Dict[str, str]] = []
    for it in items:
        try:
            typ = str(it.get("type", "")).upper()
            if want and typ not in want:
                continue
            date = str(it.get("date"))
            url_i = str(it.get("url"))
            title = it.get("title")
        except Exception:
            continue
        if not (typ and date and url_i):
            continue
        out.append({"type": typ, "date": date, "url": url_i, "title": str(title) if title is not None else ""})
    # Sort: date desc, then url asc
    out.sort(key=lambda x: (x.get("date", ""), x.get("url", "")))
    out = list(reversed(out))
    return out[: max(0, int(limit))]


def fetch_filing_text(url: str, ttl_seconds: int = 86400) -> Tuple[str, Dict[str, Any]]:
    """Fetch filing text via cache; returns (text, meta). Meta includes url, content_sha256, size, content_type, cache.
    """
    text, meta = cached_fetch_text(url, ttl_seconds=ttl_seconds)
    # Decorate meta with size/content_type (if missing)
    meta.setdefault("size", len(text.encode("utf-8")))
    meta.setdefault("content_type", "text/plain")
    return text, meta


def cache_and_snapshot(ticker: str, filing_type: str, url: str, text: str, manifest: Manifest) -> Path:
    """Write text under out/<TICKER>/filings/<sha>.txt and add a Snapshot to manifest.
    Returns file path written.
    """
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    out_dir = Path("out") / ticker.upper() / "filings"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sha}.txt"
    path.write_text(text)
    try:
        manifest.add_snapshot(Snapshot(source=filing_type, url=url, retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), content_sha256=sha, size=len(text.encode("utf-8")), content_type="text/plain"))
    except Exception:
        pass
    return path

