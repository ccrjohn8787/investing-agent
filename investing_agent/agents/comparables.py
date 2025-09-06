from __future__ import annotations

"""
Comparables agent (planned)

Selects a peer set and runs relative diagnostics. Applies only bounded, defensible
updates to InputsI (e.g., convergence of stable margin toward peer median within
limits). No LLM math.
"""

from investing_agent.schemas.inputs import InputsI


def apply(I: InputsI, peers: list[dict] | None = None, policy: dict | None = None) -> InputsI:
    """
    Comparables agent (contract stub — eval-first).

    Purpose (per paper):
    - Select peers; compute relative diagnostics (e.g., stable margin band, sales-to-capital distribution);
      propose bounded, defensible tweaks to long-run targets.

    Contract (target state):
    - Inputs: `InputsI`, optional `peers` (with fundamentals) and `policy` (bounds).
    - Output: `InputsI` with small, transparent long-run adjustments grounded in peer stats.
    - Determinism: fully deterministic given peer data.
    - Provenance: cite peer sources and computed stats.

    Current behavior: no-op, returns a deep copy of `I`.
    TODO(M5-comps): implement peer selection + stats + bounds + evals; gate router use on availability.
    """
    return I.model_copy(deep=True)
