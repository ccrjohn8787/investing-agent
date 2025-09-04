Investing Agent — Project Context and Plan

Summary
- Goal: Build a deterministic, provenance-first multi-agent system inspired by DBOT that replicates Damodaran-style valuation for long-term investing, producing transparent, backtestable reports.
- Core drivers: Sales growth, operating margin, cost of capital (WACC), reinvestment efficiency (sales-to-capital). Compatible FCF engine with end/mid-year modes and σ-based reinvestment.
- Flow: Initial waterfall (valuation → sensitivity → consensus → comparables → news) then router loop until convergence. Writer is read-only; task-based news extraction (headline → lede → full).

MVP Scope
- Data (no paid APIs): EDGAR (US fundamentals), Yahoo/Stooq (prices/splits/divs), Treasury/FRED (macro), SIC from submissions, guidance/PRs for consensus (low-trust), comps in-house, RSS news with optional NewsAPI.
- LLM: Single model (e.g., OpenAI gpt-4.1-mini) with temp=0, top_p=1, seed=2025.
- Output: Markdown + PNG, PDF optional. Tickers: NVDA, META, GOOG, UBER, TSLA. BYD as an acceptance stub.

Determinism & Provenance
- Pure NumPy kernel; LLMs deterministic when introduced. Event-sourced run log and manifest with hashes.

Acceptance (MVP)
- BYD: value band 417–468, base ≈ 420 via fixture. Deterministic runs for 5 canaries. PV/EV bridges pass. Low-trust labeling for non-filing consensus. Event log + manifest written.

Planned Structure
- investing_agent/schemas, investing_agent/kernels, connectors, agents, orchestration, scripts, fixtures, tests.

Status
- Kernel implemented: investing_agent/kernels/ginzu.py with σ-based reinvestment, end/mid-year, terminal constraint, equity bridge, per-share value.
- Schemas: InputsI, ValuationV. Tests: PV bridge, mid-year uplift band, gradient signs, terminal constraint.

Next Milestones
1) Connectors (EDGAR/Yahoo/Stooq + snapshots + provenance)
2) DC→I builder
3) Sensitivity + plotting
4) Writer + Critic
5) Consensus + Comparables v1
6) News v1
7) Supervisor + router + manifest
8) Golden fixtures + CI

Open Items
- Provide EDGAR_UA email string for SEC requests.
- Confirm OpenAI model/key availability (or skip LLM until report stage).

