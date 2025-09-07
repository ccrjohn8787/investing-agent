from __future__ import annotations

import json
import os
import time
from pathlib import Path

from investing_agent.connectors.http_cache import fetch_json


class _Resp:
    def __init__(self, data: dict):
        self._data = data
        self.headers = {"Content-Type": "application/json"}

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class _Sess:
    def __init__(self, data: dict):
        self._data = data

    def get(self, url, timeout=30):
        return _Resp(self._data)


def test_fetch_json_cache_roundtrip(tmp_path, monkeypatch):
    # Point out/_cache to a temp dir by monkeypatching the helper
    import investing_agent.connectors.http_cache as HC

    base = tmp_path / "_cache"
    base.mkdir(parents=True, exist_ok=True)

    def _cache_dir_override():
        return base

    monkeypatch.setattr(HC, "_cache_dir", _cache_dir_override)

    data = {"a": 1}
    sess = _Sess(data)
    url = "https://example.com/json"

    # First call: miss and write
    d1, meta1 = fetch_json(url, ttl_seconds=3600, session=sess)
    assert d1 == data and not meta1.get("cache")

    # Second call: hit cache
    d2, meta2 = fetch_json(url, ttl_seconds=3600, session=sess)
    assert d2 == data and meta2.get("cache") is True

    # Invalidate by aging the file
    # Change mtime to past beyond ttl
    for p in base.iterdir():
        os.utime(p, (time.time() - 4000, time.time() - 4000))
    d3, meta3 = fetch_json(url, ttl_seconds=1, session=sess)
    assert d3 == data and not meta3.get("cache")

