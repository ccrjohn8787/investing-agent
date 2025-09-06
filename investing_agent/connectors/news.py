from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import requests

from investing_agent.schemas.news import NewsItem, NewsBundle


def _hash_text(*parts: str) -> str:
    s = "\n".join(p or "" for p in parts)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def default_sources(ticker: str) -> List[Tuple[str, str]]:
    # (name, url). Yahoo Finance RSS per ticker
    return [
        ("yahoo", f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}")
    ]


def _parse_rss(xml_text: str, source: str) -> List[dict]:
    items: List[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items
    # Try RSS 2.0
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or it.findtext("published") or "").strip()
        desc = (it.findtext("description") or it.findtext("summary") or "").strip()
        items.append({
            "title": title,
            "url": link,
            "published_at": pub,
            "snippet": desc,
            "source": source,
        })
    # Basic Atom support
    for it in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = (it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link_el = it.find("{http://www.w3.org/2005/Atom}link")
        link = (link_el.get("href") if link_el is not None else "").strip()
        pub = (it.findtext("{http://www.w3.org/2005/Atom}updated") or it.findtext("{http://www.w3.org/2005/Atom}published") or "").strip()
        desc = (it.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
        items.append({
            "title": title,
            "url": link,
            "published_at": pub,
            "snippet": desc,
            "source": source,
        })
    return items


def fetch_rss(url: str, session: Optional[requests.Session] = None, timeout: int = 20) -> Tuple[List[dict], dict]:
    sess = session or requests.Session()
    resp = sess.get(url, timeout=timeout)
    resp.raise_for_status()
    text = resp.text
    items = _parse_rss(text, source=url)
    meta = {
        "url": url,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    return items, meta


def search_news(ticker: str, asof: Optional[str] = None, sources: Optional[List[Tuple[str, str]]] = None, max_items: int = 25, window_days: int = 14) -> NewsBundle:
    srcs = sources or default_sources(ticker)
    items_all: List[NewsItem] = []
    asof_dt = datetime.fromisoformat(asof.replace("Z", "+00:00")) if (asof and asof.endswith("Z")) else (datetime.utcnow().replace(tzinfo=timezone.utc))
    cutoff = asof_dt - timedelta(days=window_days)
    sess = requests.Session()
    for name, url in srcs:
        try:
            items, _meta = fetch_rss(url, session=sess)
        except Exception:
            continue
        for it in items:
            pub = it.get("published_at") or ""
            try:
                pub_dt = datetime.fromisoformat(pub)
            except Exception:
                pub_dt = asof_dt
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue
            title = (it.get("title") or "").strip()
            url0 = (it.get("url") or "").strip()
            snippet = (it.get("snippet") or "").strip()
            sha = _hash_text(title, url0, snippet)
            items_all.append(
                NewsItem(
                    id=sha[:12],
                    title=title,
                    url=url0,
                    source=name,
                    published_at=pub_dt.isoformat(),
                    snippet=snippet,
                    content_sha256=sha,
                )
            )
    # Dedup by url/content hash and sort by published_at desc then title
    seen = set()
    uniq: List[NewsItem] = []
    for it in sorted(items_all, key=lambda x: (x.published_at or "", x.title), reverse=True):
        key = (it.url or "", it.content_sha256 or "")
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
        if len(uniq) >= max_items:
            break
    return NewsBundle(ticker=ticker, asof=asof_dt.isoformat().replace("+00:00", "Z"), items=uniq)

