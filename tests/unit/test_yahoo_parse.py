from __future__ import annotations

from investing_agent.connectors.yahoo import fetch_prices_v8_chart


def test_yahoo_v8_parse(monkeypatch):
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1696032000, 1696118400],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0, 105.0],
                                "high": [110.0, 112.0],
                                "low": [95.0, 101.0],
                                "close": [105.0, 110.0],
                                "volume": [1000000, 1200000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    class Sess:
        def get(self, url, timeout=30):
            return Resp()

    ps = fetch_prices_v8_chart("NVDA", session=Sess())
    assert ps.ticker == "NVDA"
    assert len(ps.bars) == 2
    assert ps.bars[0].close == 105.0

