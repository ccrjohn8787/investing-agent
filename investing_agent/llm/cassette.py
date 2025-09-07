from __future__ import annotations

"""
Cassette record/replay utilities for deterministic LLM usage.
"""

from pathlib import Path
from typing import Any, Dict
import hashlib
import json


def _request_sha(req: Dict[str, Any]) -> str:
    b = json.dumps(req, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def record(request: Dict[str, Any], response: Dict[str, Any], path: Path) -> Dict[str, Any]:
    """Append a JSONL entry with request/response and metadata. Returns the entry dict."""
    entry = {
        "request": request,
        "response": response,
        "model_id": request.get("model_id"),
        "params": request.get("params", {}),
        "sha": _request_sha(request),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def replay(request: Dict[str, Any], path: Path) -> Dict[str, Any]:
    """Return the recorded response matching the request hash, else raises."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    target = _request_sha(request)
    with path.open() as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict) and row.get("sha") == target:
                resp = row.get("response")
                if isinstance(resp, dict):
                    return resp
    raise LookupError("No matching cassette entry")

