from __future__ import annotations

"""
Consensus agent (planned)

Maps near-term consensus/guidance into InputsI while clamping long-term drivers.
Per AGENTS.md, numeric updates are code-only; LLM may propose bounded deltas but
must flow through schema-checked code.
"""

from investing_agent.schemas.inputs import InputsI


def apply(I: InputsI) -> InputsI:
    """Return updated InputsI (placeholder: no-op)."""
    # TODO: inject near-term explicit values if consensus available; clamp long-term
    return I

