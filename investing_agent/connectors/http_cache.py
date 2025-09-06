from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional, Tuple

import requests


def _cache_dir() -> Path:
    p = Path("out") / "_cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def fetch_text(url: str, ttl_seconds: int = 86400, session: Optional[requests.Session] = None, timeout: int = 30) -> Tuple[str, dict]:
    """
    Fetch URL with a simple disk cache (text). Returns (text, meta).
    Cache path: out/_cache/<sha>.txt and .meta.json (implicit via returned meta).
    """
    sess = session or requests.Session()
    key = _key(url)
    cache_path = _cache_dir() / f"{key}.txt"
    now = int(time.time())
    if cache_path.exists():
        mtime = int(cache_path.stat().st_mtime)
        if now - mtime <= ttl_seconds:
            text = cache_path.read_text()
            meta = {
                "url": url,
                "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime)),
                "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "cache": True,
            }
            return text, meta
    resp = sess.get(url, timeout=timeout)
    resp.raise_for_status()
    text = resp.text
    cache_path.write_text(text)
    meta = {
        "url": url,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "cache": False,
    }
    return text, meta

