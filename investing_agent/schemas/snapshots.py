from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Snapshot(BaseModel):
    source: str
    endpoint: Optional[str] = None
    retrieved_at: Optional[str] = None
    license: Optional[str] = None
    content_sha256: Optional[str] = None
    notes: Optional[str] = None

