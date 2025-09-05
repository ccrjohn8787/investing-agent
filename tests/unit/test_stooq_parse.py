from __future__ import annotations

from investing_agent.connectors.stooq import fetch_prices


def test_stooq_parse_csv(monkeypatch):
    sample = """Date,Open,High,Low,Close,Volume\n2024-09-30,100,110,95,105,1000000\n2024-10-01,105,112,101,110,1200000\n"""

    class Resp:
        status_code = 200
        text = sample

        def raise_for_status(self):
            pass

    class Sess:
        def get(self, url, timeout=30):
            return Resp()

    ps = fetch_prices("NVDA", session=Sess())
    assert ps.ticker == "NVDA"
    assert len(ps.bars) == 2
    assert ps.bars[0].close == 105.0

