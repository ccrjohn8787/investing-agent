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
- investing_agent/schemas: Typed objects for inputs and outputs.
- investing_agent/kernels: Valuation kernel (ginzu) pure NumPy.
- tests: Unit and integration tests for kernel correctness and determinism.

Getting Started
- Create a virtual environment and install dev deps:
  python -m venv .venv && . .venv/bin/activate
  pip install -e .[dev]
- Run tests: pytest -q

