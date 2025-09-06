from __future__ import annotations

"""
Market agent (planned)

Applies bounded, schema-checked transforms to InputsI to reconcile structural
assumptions (e.g., WACC path, beta) with market context. No direct LLM math.
"""

from investing_agent.schemas.inputs import InputsI


def apply(I: InputsI, context: dict | None = None) -> InputsI:
    """
    Market reconciliation agent (contract stub — eval-first).

    Purpose (per paper):
    - When asked to reconcile intrinsic value to market price, find the smallest
      bounded changes to the value drivers that match the observed market price,
      with a transparent rationale and provenance.

    Contract (target state):
    - Inputs: `InputsI`, optional `context` with
      {"target_price", "weights", "bounds", "penalties"}.
    - Output: new `InputsI` with proposed deltas; numeric changes derive from a
      code solver (least-squares with bounds), never from an LLM.
    - Determinism: fully deterministic given inputs and bounds.
    - Provenance: record rationale and constraints in event log; cite snapshots.

    Current behavior: no-op, returns a deep copy of `I`.
    TODO(M5-market): implement bounded solver + evals; gate router use on data.
    """
    return I.model_copy(deep=True)
