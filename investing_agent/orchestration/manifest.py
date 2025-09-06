from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def _git_head_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


@dataclass
class Snapshot:
    source: str
    url: Optional[str] = None
    retrieved_at: Optional[str] = None
    content_sha256: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    license: Optional[str] = None


@dataclass
class Manifest:
    run_id: str
    ticker: str
    asof: Optional[str] = None
    code_sha: str = field(default_factory=_git_head_sha)
    models: Dict[str, str] = field(default_factory=dict)
    snapshots: List[Snapshot] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)

    def add_snapshot(self, snap: Snapshot) -> None:
        self.snapshots.append(snap)

    def add_artifact(self, name: str, data: Any) -> None:
        b = _to_bytes(data) or b""
        self.artifacts[name] = _sha256_bytes(b)

    def write(self, path: Path) -> None:
        obj = {
            "run_id": self.run_id,
            "ticker": self.ticker,
            "asof": self.asof,
            "code_sha": self.code_sha,
            "models": self.models,
            "snapshots": [s.__dict__ for s in self.snapshots],
            "artifacts": self.artifacts,
        }
        path.write_text(json.dumps(obj, indent=2))
