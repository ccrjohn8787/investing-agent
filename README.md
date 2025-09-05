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
- `investing_agent/schemas`: Typed objects for inputs, outputs, and fundamentals.
- `investing_agent/kernels`: Valuation kernel (Ginzu) pure NumPy + public `series()` API for per‑year arrays.
- `investing_agent/agents`: Builder (valuation), sensitivity, plotting, Markdown writer, HTML writer, critic.
- `investing_agent/connectors`: EDGAR (US‑GAAP + IFRS fallbacks), Stooq/Yahoo (prices), UST (risk‑free).
- `scripts`: Demo and reporting CLI with overrides/config.
- `tests`: Unit tests for kernel, connectors, sensitivity, writers, and CLI helpers.

Getting Started
- Create a virtual environment and install dev deps:
  - `python -m venv .venv && . .venv/bin/activate`
  - `pip install -e .[dev]`
  - Optional (for YAML configs): `pip install pyyaml`
- Run tests: `pytest -q`

Demo (no network required)
- Generate a synthetic end-to-end report and plots:
  - `make demo`
  - Outputs under `./out/`: `SYN_report.md`, `SYN_sensitivity.png`, `SYN_drivers.png`

Connectors (when fetching live data)
- EDGAR requires a User‑Agent per SEC rules. Example:
  - `export EDGAR_UA="you@example.com Investing-Agent/0.1"`
- Prices via Stooq use CSV; no key required. Yahoo v8 used as fallback.
- Fundamentals parsing covers common US‑GAAP tags and IFRS fallbacks (revenue, operating profit, shares, tax, D&A, capex, leases, working capital).
- Demo is offline; reporting CLI can operate offline on cached inputs and companyfacts.

Reports
- Build inputs from EDGAR and cache locally: `make build_i CT=<TICKER>`
- Generate full report (uses cached inputs if present): `make report CT=<TICKER>`
- Force fresh fundamentals (bypass cache): `python scripts/report.py --fresh <TICKER>`
- Override drivers from CLI: `python scripts/report.py <TICKER> --growth '8%,7%' --margin '12%,13%' --s2c '2.0,2.2'`
- Use config for advanced settings (horizon, discounting, beta, macro, stable targets, and driver paths):
  - `python scripts/report.py <TICKER> --config path/to/config.yaml` (YAML) or `.json`
  - CLI flags take precedence over config values.
- Export HTML (single‑file) alongside Markdown: add `--html`.

Artifacts
- Markdown: `out/<TICKER>/report.md`
- HTML (if `--html`): `out/<TICKER>/report.html`
- Series CSV (per‑year revenue/EBIT/FCFF/WACC/DF/PV): `out/<TICKER>/series.csv`
- Fundamentals CSV (parsed annual fields): `out/<TICKER>/fundamentals.csv`
- Raw EDGAR companyfacts (if fetched): `out/<TICKER>/companyfacts.json`

Report Contents
- Summary KPIs: value per share, equity value, PV explicit/terminal, shares.
- Drivers & assumptions: discounting mode, tax, stable growth/margin, sales‑to‑capital, WACC, net debt/cash.
- Per‑year detail: revenue, growth, margin, sales‑to‑capital, ROIC, reinvestment, FCFF, WACC, discount factor, PV(FCFF).
- Terminal value: FCFF(T+1), r−g, TV@T, DF@T, PV(TV).
- Fundamentals (parsed): annual revenue/EBIT table, TTM revenue/EBIT, shares, tax, D&A, capex, lease assets/liabilities, working capital.
- HTML only: embedded charts (sensitivity, drivers) and collapsible raw companyfacts JSON (for transparency).

CLI Options
- `--growth`, `--margin`, `--s2c`: comma‑separated paths; accepts percents (`"8%"`) or decimals (`0.08`).
- `--config`: JSON or YAML file with any of: `growth`, `margin`, `s2c`, `horizon`, `discounting` (`end|midyear`), `beta`, `stable_growth`, `stable_margin`, `macro` (`risk_free_curve`, `erp`, `country_risk`).
- `--fresh`: bypass caches and refetch companyfacts and macro.
- `--html`: write a single‑file HTML report alongside Markdown and CSVs.

Example `config.yaml`
```
horizon: 12
discounting: midyear
beta: 1.1
stable_growth: 0.025
stable_margin: 0.18
growth: ["8%", "7%", "6%", "5%"]
margin: [0.16, 0.17, 0.18]
s2c: [2.0, 2.1, 2.2]
macro:
  risk_free_curve: [0.04, 0.04, 0.04]
  erp: 0.05
  country_risk: 0.0
```

Notes & Limits
- IFRS coverage is pragmatic; tag coverage expands as needed.
- WACC path = rf + (ERP + country risk) × beta; leverage/tax shield modeling is minimal in MVP.
- EDGAR rate limits apply; set `EDGAR_UA` and be respectful with fetches.
