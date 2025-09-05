from __future__ import annotations

"""
Market agent (planned)

Applies bounded, schema-checked transforms to InputsI to reconcile structural
assumptions (e.g., WACC path, beta) with market context. No direct LLM math.
"""

from investing_agent.schemas.inputs import InputsI


def apply(I: InputsI) -> InputsI:
    """Return updated InputsI (placeholder: no-op)."""
    # TODO: implement bounded tweaks (e.g., adjust WACC path, beta) with justification
    return I

