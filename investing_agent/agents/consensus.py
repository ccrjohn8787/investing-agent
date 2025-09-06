from __future__ import annotations

"""
Consensus agent (planned)

Maps near-term consensus/guidance into InputsI while clamping long-term drivers.
Per AGENTS.md, numeric updates are code-only; LLM may propose bounded deltas but
must flow through schema-checked code.
"""

from investing_agent.schemas.inputs import InputsI


def apply(I: InputsI, consensus_data: dict | None = None) -> InputsI:
    """
    Consensus agent (contract stub — eval-first).

    Purpose (per paper):
    - Obtain analyst consensus/guidance and map to near-term spreadsheet drivers
      (first N years), while clamping long-term drivers to stable targets.

    Contract (target state):
    - Inputs: `InputsI`, optional `consensus_data` schema with vendor fields.
    - Output: new `InputsI` with near-term overrides; numeric mapping done in code; bounds enforced.
    - Determinism: fully deterministic given consensus input.
    - Provenance: cite consensus snapshots; record mapping and clamps.

    Current behavior: no-op, returns a deep copy of `I`.
    TODO(M5-consensus): implement connectors + mapping + evals; gate router use on availability.
    """
    return I.model_copy(deep=True)
