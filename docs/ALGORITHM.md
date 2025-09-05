## DBOT Algorithm (paper-aligned, repo-bound)

This document specifies the end‑to‑end valuation and report generation algorithm in this repo, aligned with the paper’s Algorithm 1. It binds each abstract step to concrete modules and functions, and clarifies our determinism and auditability rules.

### Symbols and core functions

- Inputs: `Cn` company name, `Ct` ticker, `DC` raw data bundle (companyfacts JSON etc.), `F` parsed fundamentals, `I` kernel inputs, `v` valuation, `R` report.
- Kernel: `f_fcf : I → v` → `investing_agent.kernels.ginzu.value(I)`
- DC→F→I mapping (code only):
  - `F = parse_companyfacts_to_fundamentals(DC)`
  - `I = build_inputs_from_fundamentals(F, …)`
- Sensitivity (read‑only analysis): `compute_sensitivity(I)`
- Plotting (deterministic): `plot_sensitivity_heatmap`, `plot_driver_paths`
- Writer (deterministic): `render_report`, optional `render_html_report`
- Event log + Manifest: JSONL run log and `manifest.json` with snapshots and artifact hashes

LLM boundaries (per AGENTS.md)
- Only News/Writer/Critic may use LLMs; numeric work remains in code.
- Determinism for any LLM use: `temperature=0`, `top_p=1`, `seed=2025`.
- LLM proposals (if any) flow through bounded, schema‑checked code transforms.

### Prompt contracts (short)
- `P_DC→I`  Map DC→I (strict JSON schema, no invented fields).
- `P_market` Minimal squared change to reconcile intrinsic value to market cap (bounded).
- `P_consensus` Map near‑term consensus/guidance into I; clamp long‑term drivers.
- `P_comparables` Peer selection + relative diagnostics; apply only defensible bounded tweaks.
- `P_news` Extract valuation‑relevant facts; propose driver deltas with horizon and confidence.
- `P_router` Choose one next step from {market, sensitivity, consensus, comparables, news, end}.
- `P_{I,v→R}` Write report from I and v. No new numbers. Cite sources by snapshot IDs.

### Algorithm (faithful flow)

```
INIT
  P_DC→I := prompt for DC→I (reference only; our pipeline is code-based)

INITIAL VALUATION
  F  := parse_companyfacts_to_fundamentals(DC)
  I  := build_inputs_from_fundamentals(F, …)
  v  := f_fcf(I)

INITIAL WATERFALL  (each step logs event and updates artifacts)
  # market/consensus/comparables are code transforms to I (bounded)
  I' := agents.market.apply(I)        ; v := f_fcf(I')
  I' := agents.consensus.apply(I')    ; v := f_fcf(I')
  I' := agents.comparables.apply(I')  ; v := f_fcf(I')
  # sensitivity is analysis‑only; computes grid/plots; does NOT mutate I
  S  := compute_sensitivity(I')       ; figures := plot(S, I')
  # optional: news ingestion (LLM proposal → bounded code updates)
  I' := agents.news.ingest_and_update(I', v, s(Ct)) ; v := f_fcf(I')

ROUTER LOOP (bounded, deterministic first; LLM router optional)
  while not converged and iters < Nmax:
    {route, instruction} := router.choose_next(I', v, context)
    case route of
      market      : I' := agents.market.apply(I')       ; v := f_fcf(I')
      consensus   : I' := agents.consensus.apply(I')    ; v := f_fcf(I')
      comparables : I' := agents.comparables.apply(I')  ; v := f_fcf(I')
      news        : I' := agents.news.ingest_and_update(I', v, s(Ct)) ; v := f_fcf(I')
      sensitivity : S := compute_sensitivity(I') ; figures := plot(S, I')
      end         : break

VALUATION + REPORT (traceable)
  F  := parse_companyfacts_to_fundamentals(DC)       # regenerate for provenance
  I* := build_inputs_from_fundamentals(F, …)
  v* := f_fcf(I*)
  R  := writer.render_report(I*, v*, figures, fundamentals=F)
  # optional: html_writer.render_html_report(…)
```

### Convergence and determinism
- Converged when all hold:
  - |Δ value_per_share| ≤ 0.5% over two consecutive router steps; and
  - no new admitted news with estimated impact ≥ 1.0% Δ value_per_share; and
  - critic has zero blockers; and
  - router returns `end`.
- Guards: cap loop at Nmax (e.g., 10) and break early if `InputsI` unchanged for 2 consecutive steps.
- Determinism: temperature 0, `top_p=1`, fixed seed; ordered retrieval; idempotent writes; stable tie‑breaks.

### Module bindings (current vs planned)

Current
- Kernel: `investing_agent.kernels.ginzu.value`, `ginzu.series`
- DC→F→I: `investing_agent.connectors.edgar.parse_companyfacts_to_fundamentals` → `investing_agent.agents.valuation.build_inputs_from_fundamentals`
- Sensitivity: `investing_agent.agents.sensitivity.compute_sensitivity`
- Plotting: `investing_agent.agents.plotting.plot_sensitivity_heatmap`, `plot_driver_paths`
- Writer: `investing_agent.agents.writer.render_report`, `agents.html_writer.render_html_report`
- Orchestration (audit): `investing_agent.orchestration.eventlog.EventLog`, `manifest.Manifest`

Planned (stubs)
- Market: `investing_agent.agents.market.apply(I)`
- Consensus: `investing_agent.agents.consensus.apply(I)`
- Comparables: `investing_agent.agents.comparables.apply(I)`
- News: `investing_agent.agents.news.search_news(Ct)`, `ingest_and_update(I, v, news)`
- Router: `investing_agent.agents.router.choose_next(I, v, context)` (deterministic first)
- FSM Orchestrator: `investing_agent.orchestration.fsm.Orchestrator`

### ASCII overview
```
[DC] -> parse -> F -> build -> I0 -> f_fcf -> v0
   -> market -> v1
   -> consensus -> v2
   -> comparables -> v3
   -> sensitivity (plots)
   -> news(s(Ct)) -> v4
   -> Router loop* -> v*
   -> Writer -> Report
```

### Notes
- Sensitivity is read‑only; its role is analysis and transparency, not mutation of I.
- All updates to `I` occur only through bounded, schema‑checked code paths to preserve auditability.
- Event log and manifest record every step, with external snapshots (EDGAR, UST, prices) and artifact hashes.

