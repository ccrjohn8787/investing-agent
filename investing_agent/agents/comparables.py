from __future__ import annotations

"""
Comparables agent (planned)

Selects a peer set and runs relative diagnostics. Applies only bounded, defensible
updates to InputsI (e.g., convergence of stable margin toward peer median within
limits). No LLM math.
"""

from investing_agent.schemas.inputs import InputsI


def apply(I: InputsI) -> InputsI:
    """Return updated InputsI (placeholder: no-op)."""
    # TODO: compute peer stats and apply bounded adjustments with rationale
    return I

