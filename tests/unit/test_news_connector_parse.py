from __future__ import annotations

from investing_agent.connectors.news import _parse_rss


def test_parse_rss_basic_items():
    rss = """
    <rss version="2.0"><channel>
      <item><title>Headline A</title><link>http://example.com/a</link><pubDate>2025-09-01T00:00:00Z</pubDate><description>Desc A</description></item>
      <item><title>Headline B</title><link>http://example.com/b</link><pubDate>2025-09-02T00:00:00Z</pubDate><description>Desc B</description></item>
    </channel></rss>
    """
    items = _parse_rss(rss, source="test")
    assert len(items) == 2
    assert items[0]["title"] == "Headline A"
    assert items[0]["url"].endswith("/a")
    assert items[0]["source"] == "test"

