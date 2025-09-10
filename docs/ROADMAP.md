## DBOT Roadmap and Milestones

This roadmap captures the end goal, success criteria, milestones, and current status for building a faithful, production‑grade DBOT based on the paper and Algorithm 1.

### Final Goal (North Star)
- Deliver a deterministic, provenance‑first multi‑agent valuation system that:
  - Ingests public data (EDGAR, UST, prices) with full snapshots and hashes.
  - Produces an auditable intrinsic valuation with transparent assumptions and per‑year tables.
  - Follows the paper’s Algorithm 1 with an initial deterministic router and bounded, schema‑checked updates to inputs.
  - Generates self‑contained reports (Markdown + HTML) with embedded charts and citations that map to snapshot IDs or computed tables.
- Product shape: Python library + CLI (optionally a thin web UI later), producing a directory of artifacts per run: `report.md`, `report.html`, charts, `series.csv`, `fundamentals.csv`, `companyfacts.json`, `run.jsonl`, `manifest.json`.

### Success Criteria (How we evaluate)
- Reproducibility: 100% byte‑for‑byte repeatability given same inputs (manifest hashes match) on 20+ canary tickers.
- Determinism: All numeric work is code; any LLM usage (News/Writer/Critic only) is `temp=0`, `top_p=1`, `seed=2025` and proposals are enforced via code.
- Auditability: Every external claim cites a snapshot ID (URL, retrieved_at, content hash) or a computed table; event log and manifest present for every run.
- Quality gates:
  - Kernel invariants: PV bridge, terminal constraints, sensitivity monotonicity.
  - Report completeness: drivers, per‑year tables, terminal breakdown, fundamentals section.
  - Router convergence: ≤10 iterations; |Δ value_per_share| ≤0.5% across two steps; no admitted impactful news ≥1% pending; critic=0 blockers.
- Performance: End‑to‑end run (fresh) ≤60s typical, ≤120s P95 (network bound); cached ≤10s.

### Milestones
- M0 Core kernel + tests (PV bridge, uplift, gradients, terminal constraint) — DONE
- M1 Reports v1: per‑year detail, terminal breakdown, charts, fundamentals section — DONE
- M2 Audit & provenance: `run.jsonl` event log + `manifest.json` with EDGAR snapshot — DONE
- M3 Algorithm plan + agent rules: `docs/ALGORITHM.md`, `AGENTS.md` — DONE
- M4 Deterministic router (rule‑based) returning next step + guards — DONE
- M5 Agents v1 (code‑only): market/consensus/comparables bounded transforms — DONE (market solver, comparables cap, consensus mapping + smoothing; evals/tests)
- M6 News v1: deterministic retrieval; bounded ingest; optional deterministic summary — DONE (heuristics + cassette-based LLM evals; CLI/supervisor integration; tests/evals)
- M7 Manifest snapshots extended: add UST and prices (URL + meta; hash when available) — DONE (size/content_type added)
- M8 Citations enforcement: report maps claims to snapshot IDs or computed tables — DONE
- M9 Golden fixtures & CI gates: canary tickers, acceptance checks, artifact hash pinning — DONE (infrastructure: writer script, acceptance test, Make targets; add/maintain goldens via team policy)
- M10 CLI polish: scenario YAML, multi‑ticker batch, richer flags; CSV/JSON exports — DONE (scenario + batch + flags)
- M11 Caching & performance: local caches with revalidation; parallel fetch where safe — PENDING
- M11.5 Research v1 (evidence and insights): NEW
  - Deterministic retrieval of filings/news text (10-K/10-Q MD&A, 8-Ks, IR RSS); cache under `out/<TICKER>/filings/` with hashes.
  - Contract: `schemas/research.py::InsightCard`, `InsightBundle` — claims with quotes, snapshot IDs, driver tags, horizon, confidence, rationale.
  - LLM usage boundary: InsightCards generation is performed under the Writer agent (LLM) using these retrieved texts; Research remains retrieval + structuring.
  - Evals: coverage (min cards), citation density (≥1 snapshot per card), driver tags in allowed set, presence of quotes; cassette-based outputs.
  - Artifacts: `insights.json` added to manifest artifacts; models recorded when LLM is involved.
- M12 Writer/Critic (LLM) gating: UPDATED
  - Writer (LLM) hybrid path: generate narrative JSON (`schemas/writer_llm.py::WriterLLMOutput`) with sections [Business Model, Thesis, What Changed, Drivers, Risks, Scenarios, Market vs Value], using tokens like `[ref:computed:…]`, `[table:…]`, `[section:…]`, `[snap:<sha>]`.
  - Post-processor merges LLM sections with existing tables/charts; no LLM-introduced numbers. Rule-based Critic validates tokens, arithmetic, sections; optional LLM Critic flags style/unsupported claims.
  - Evals: structure checks (required sections present), token-only numerics (min paragraphs with `[ref:]`), citations present; cassette-based.
  - CLI: `--writer llm|code|hybrid`; manifest `models` updated with deterministic params.
- M13 Orchestrator FSM: structured flow with router loop + stop conditions — PENDING
- M14 Web UI (optional): single‑file HTML viewer + lightweight UI — OPTIONAL

### Current Status (2025‑Q1)

**Completed Initiatives:**
- ✅ **DBOT Quality Gap (P0-P7):** Professional report generation system with LLM narratives
- ✅ **Evidence Pipeline:** Research-once-then-freeze architecture with full auditability
- ✅ **Evaluation Framework:** 5-dimensional quality scoring with BYD benchmark
- ✅ **API Safety:** Cost controls with GPT-4o-mini as default model
- ✅ **Professional Writer:** Story-to-numbers narrative generation with citations

**Current Initiative:**
- 🚧 **P8 Interactive UI:** Modern HTML interface with evaluation score integration (see `docs/UI_ARCHITECTURE.md`)

**Next Priorities:**
- Web-based report viewer with interactive DCF model
- Real-time collaboration features
- Mobile-responsive design
- Advanced export capabilities
- Kernel, reports, audit trail, and algorithm spec are in place. Router heuristics have unit coverage. Market solver and comparables are implemented with bounds; consensus maps near‑term and trends the tail back to stable. Manifest snapshots include EDGAR/UST/prices with size/content_type. CI runs ruff/mypy/pytest on 3.11/3.12.

### Next Actions (near‑term)
1) Consensus (M5 finalize): add optional smoothing parameters (scenario‑driven slope/half‑life), evals for bounds and tail behavior.
2) LLM Writer v1 (M12): implement WriterLLM contracts, post‑processor, and add evals + cassettes; keep numeric integrity via tokens and Critic.
3) Research v1 (M11.5): build retrieval + structuring; add sample InsightCards cassette and evals; wire artifacts into manifest.
4) Router (M4 polish): add supervisor loop integration test and convergence thresholds as config; ensure sensitivity run occurs once near convergence.
5) Golden canaries (M9): add 2–3 ticker fixtures with goldens; wire gating in CI; record manifest deltas and critic pass; extend to include narrative JSON when LLM Writer is enabled.
6) Caching & perf (M11): generalize caches outside `out/<TICKER>/` with revalidation and TTL; add controlled parallel fetch for EDGAR/UST/prices where safe; reuse cache in Research.

### Risks & Mitigations
- Upstream instability (SEC/UST/price endpoints): cache artifacts with hashes; degrade gracefully; annotate report.
- Scope creep on LLM usage: enforce AGENTS.md boundaries; keep numeric work in code; require deterministic settings and code validation paths. Research LLM work happens under Writer agent; use cassettes and strict schemas.
- Non‑deterministic ordering: enforce sorted inputs, stable tie‑breakers, idempotent writes.

### Keeping This Updated
- Update this file when milestones are completed or re‑scoped (PRs should reference a milestone ID).
- Consider a lightweight CHANGELOG and GitHub project board to mirror milestones.
