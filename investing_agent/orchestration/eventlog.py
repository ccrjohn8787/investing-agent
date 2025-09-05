from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _to_bytes(obj: Any) -> Optional[bytes]:
    if obj is None:
        return None
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj)
    if isinstance(obj, str):
        return obj.encode("utf-8")
    try:
        return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except Exception:
        return None


@dataclass
class Event:
    ts: str
    agent: str
    params_sha: Optional[str]
    input_sha: Optional[str]
    output_sha: Optional[str]
    duration_ms: Optional[int]
    notes: Optional[str] = None


class EventLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        *,
        agent: str,
        params: Any = None,
        inputs: Any = None,
        outputs: Any = None,
        duration_ms: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> None:
        ps = _to_bytes(params)
        ins = _to_bytes(inputs)
        outs = _to_bytes(outputs)
        row = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "agent": agent,
            "params_sha": _sha256_bytes(ps) if ps else None,
            "input_sha": _sha256_bytes(ins) if ins else None,
            "output_sha": _sha256_bytes(outs) if outs else None,
            "duration_ms": int(duration_ms) if duration_ms is not None else None,
            "notes": notes,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

