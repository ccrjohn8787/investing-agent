from __future__ import annotations

import json
from pathlib import Path

from investing_agent.connectors.filings import fetch_filings_index, fetch_filing_text, extract_text, cache_and_snapshot
from investing_agent.orchestration.manifest import Manifest


def test_index_parsing_and_ordering(monkeypatch, tmp_path):
    # Load fixture JSON and monkeypatch http_cache.fetch_json to return it
    fixture = json.loads(Path("tests/fixtures/filings/index_sample.json").read_text())

    def fake_fetch_json(url, ttl_seconds=86400, session=None, timeout=30):
        return fixture, {"url": url, "retrieved_at": "2025-01-01T00:00:00Z", "content_sha256": "x", "cache": False}

    import investing_agent.connectors.filings as FL
    monkeypatch.setattr(FL, "cached_fetch_json", fake_fetch_json)
    items = fetch_filings_index("XYZ", types=["10-K", "10-Q", "8-K"], limit=3)
    # Expect sorted by date desc: 10-Q (2024-05-10), 8-K (2024-03-05), 10-K (2024-02-20)
    assert [it["type"] for it in items] == ["10-Q", "8-K", "10-K"]
    assert all(it.get("url") for it in items)


def test_extract_text_variants():
    html_10k = Path("tests/fixtures/filings/10k_mda_sample.html").read_text()
    text_10k = extract_text(html_10k, kind="10-K")
    assert text_10k and "Management's Discussion and Analysis".lower().replace("'", "")[:10] in text_10k.lower()
    # Idempotent
    assert extract_text(html_10k, kind="10-K") == text_10k

    html_8k = Path("tests/fixtures/filings/8k_body_sample.html").read_text()
    text_8k = extract_text(html_8k, kind="8-K")
    assert text_8k and "registrant announces new product" in text_8k.lower()


def test_caching_write_and_snapshot(tmp_path, monkeypatch):
    # Simulate fetching text and then caching + snapshot recording
    ticker = "TEST"
    url = "https://edgar.example/a10k.html"
    text = "Hello MD&A world"
    manifest = Manifest(run_id="t", ticker=ticker)
    # Write and snapshot
    p = cache_and_snapshot(ticker, "10-K", url, text, manifest)
    assert p.exists()
    # Snapshot present with expected fields
    snaps = manifest.snapshots
    assert snaps and snaps[-1].source == "10-K" and snaps[-1].url == url
    assert snaps[-1].content_sha256 is not None
