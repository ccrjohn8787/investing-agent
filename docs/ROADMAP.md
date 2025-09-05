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
- M4 Deterministic router (rule‑based) returning next step + guards — PENDING
- M5 Agents v1 (code‑only): market/consensus/comparables bounded transforms — PENDING
- M6 News v1: deterministic retrieval; bounded ingest; optional deterministic summary — PENDING
- M7 Manifest snapshots extended: add UST and prices (URL + meta; hash when available) — PARTIAL (URL recorded)
- M8 Citations enforcement: report maps claims to snapshot IDs or computed tables — PENDING
- M9 Golden fixtures & CI gates: canary tickers, acceptance checks, artifact hash pinning — PENDING
- M10 CLI polish: scenario YAML, multi‑ticker batch, richer flags; CSV/JSON exports — PENDING
- M11 Caching & performance: local caches with revalidation; parallel fetch where safe — PENDING
- M12 Writer/Critic (LLM) gating: deterministic prompts; critic blocks unsafe changes — PENDING
- M13 Orchestrator FSM: structured flow with router loop + stop conditions — PENDING
- M14 Web UI (optional): single‑file HTML viewer + lightweight UI — OPTIONAL

### Current Status (2025‑Q3)
- Kernel, reports, audit trail, and algorithm spec are in place. Agent stubs exist for router/market/consensus/comparables/news. Manifest snapshots now include EDGAR (with hash) and URLs for UST/prices. CI runs ruff/mypy/pytest on 3.11/3.12. All tests passing.

### Next Actions (near‑term)
1) Implement a deterministic router heuristic (M4) and add unit tests.
2) Implement minimal market/consensus/comparables transforms (M5) + tests and docstrings outlining bounds.
3) Wire citations in the report to manifest snapshot IDs (M8) and add tests asserting presence.
4) Extend UST/prices connectors to expose retrieval meta (timestamp + raw content when feasible) to include hashes in snapshots (finish M7).

### Risks & Mitigations
- Upstream instability (SEC/UST/price endpoints): cache artifacts with hashes; degrade gracefully; annotate report.
- Scope creep on LLM usage: enforce AGENTS.md boundaries; keep numeric work in code; require deterministic settings and code validation paths.
- Non‑deterministic ordering: enforce sorted inputs, stable tie‑breakers, idempotent writes.

### Keeping This Updated
- Update this file when milestones are completed or re‑scoped (PRs should reference a milestone ID).
- Consider a lightweight CHANGELOG and GitHub project board to mirror milestones.

