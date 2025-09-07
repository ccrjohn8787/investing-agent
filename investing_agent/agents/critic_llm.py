from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
from pathlib import Path

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def check(report_md: str, I: InputsI, V: ValuationV, cassette_path: Optional[str] = None) -> List[str]:
    """
    Deterministic LLM Critic shim (cassette-only).
    - If cassette_path provided, load JSON of the form:
      {"issues": [{"message": str, "severity": "error|warn", "code": str}]}
      and return ["{severity}:{code}:{message}"]
    - Else: return [] (no-op for now)
    """
    if not cassette_path:
        return []
    try:
        text = Path(cassette_path).read_text()
        data = json.loads(text)
        items = data.get("issues", []) if isinstance(data, dict) else []
        out: List[str] = []
        for it in items:
            try:
                sev = str(it.get("severity", "warn"))
                code = str(it.get("code", "GEN"))
                msg = str(it.get("message", ""))
            except Exception:
                continue
            out.append(f"{sev}:{code}:{msg}")
        return out
    except Exception:
        return []

