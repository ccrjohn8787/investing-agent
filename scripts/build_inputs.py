#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from investing_agent.agents.valuation import build_inputs_from_fundamentals
from investing_agent.connectors.edgar import fetch_companyfacts, parse_companyfacts_to_fundamentals


def main():
    ticker = os.environ.get("CT") or os.environ.get("TICKER")
    if not ticker:
        raise SystemExit("Set CT=<TICKER> or TICKER env var")
    edgar_ua = os.environ.get("EDGAR_UA")
    if not edgar_ua:
        print("Warning: EDGAR_UA not set; SEC requests may be blocked.")

    cf_json, meta = fetch_companyfacts(ticker, edgar_ua=edgar_ua)
    f = parse_companyfacts_to_fundamentals(cf_json, ticker=ticker)
    I = build_inputs_from_fundamentals(f, horizon=10)

    out_dir = Path("out") / ticker.upper()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "companyfacts.json").write_text(json.dumps(cf_json))
    (out_dir / "inputs.json").write_text(I.model_dump_json(indent=2))
    print(f"Wrote inputs to {out_dir}")


if __name__ == "__main__":
    main()

