Investing Agent (MVP)

Overview
- Deterministic, provenance-first valuation pipeline with a compatible FCF engine ("Ginzu") using four drivers: sales growth, operating margin, cost of capital (WACC), and reinvestment efficiency (sales-to-capital).
- No paid APIs in v1. US fundamentals via SEC EDGAR, prices via Yahoo/Stooq, macro via Treasury/FRED.
- Initial focus on end-to-end single-ticker reports (Markdown + PNGs). Backtesting harness stubbed for post-MVP.

Determinism
- Numeric computation is pure NumPy and fully reproducible.
- Future LLM usage will fix temp=0, top_p=1, seed.
- All artifacts carry source URLs and content hashes.

Structure
- `investing_agent/schemas`: Typed objects for inputs and outputs.
- `investing_agent/kernels`: Valuation kernel (ginzu) pure NumPy.
- `investing_agent/agents`: Input builder, sensitivity, plotting, writer, critic.
- `investing_agent/connectors`: EDGAR, Stooq, Yahoo, UST.
- `tests`: Unit tests for kernel, connectors, sensitivity.

Getting Started
- Create a virtual environment and install dev deps:
  - `python -m venv .venv && . .venv/bin/activate`
  - `pip install -e .[dev]`
- Run tests: `pytest -q`

Demo (no network required)
- Generate a synthetic end-to-end report and plots:
  - `make demo`
  - Outputs under `./out/`: `SYN_report.md`, `SYN_sensitivity.png`, `SYN_drivers.png`

Connectors (when fetching live data)
- EDGAR requires a User-Agent per SEC rules. Example:
  - `export EDGAR_UA="you@example.com Investing-Agent/0.1"`
- Prices via Stooq use CSV; no key required.
- Network calls are not used in the demo; connectors are implemented for later use.

Reports
- Build inputs from EDGAR and cache locally: `make build_i CT=<TICKER>`
- Generate full report (uses cached inputs if present): `make report CT=<TICKER>`
- Force fresh fundamentals (bypass cache): `python scripts/report.py --fresh <TICKER>`
- Override drivers from CLI: `python scripts/report.py <TICKER> --growth '8%,7%' --margin '12%,13%' --s2c '2.0,2.2'`
- Use JSON config for advanced settings (horizon, discounting, beta, macro, stable targets):
  - `python scripts/report.py <TICKER> --config path/to/config.json`
  - CLI flags take precedence over config values.
- Export HTML (single-file) alongside Markdown: add `--html`.

Artifacts
- Markdown: `out/<TICKER>/report.md`
- HTML (if `--html`): `out/<TICKER>/report.html`
- Series CSV: `out/<TICKER>/series.csv`
- Raw EDGAR companyfacts (if fetched): `out/<TICKER>/companyfacts.json`
