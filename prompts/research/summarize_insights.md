Deterministic Research Summarizer (Cassette-Driven)

Goal
- Produce an InsightBundle JSON from cached filings/news text.
- No numeric computations; do not introduce new numbers. Claims must be qualitative.

Output Schema
- cards: array of InsightCard
  - claim: string (no naked numbers)
  - tags: subset of {growth, margin, s2c, wacc, other}
  - start_year_offset: int; end_year_offset: int
  - confidence: float (0..1)
  - quotes: array of { text: string, snapshot_ids: [sha], sources: [url] }
- Every card must have ≥1 quote and snapshot_ids.

Determinism
- Parameters: temperature=0, top_p=1, seed=2025
- Stable ordering as supplied by inputs.

Citation Rules
- Each quote must include snapshot_ids; include sources when available.
- Claims reference quotes or computed sections indirectly; no live lookups.

