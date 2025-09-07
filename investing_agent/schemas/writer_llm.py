from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WriterSection(BaseModel):
    title: str
    paragraphs: List[str] = Field(default_factory=list)
    refs: List[str] = Field(default_factory=list)


class WriterLLMOutput(BaseModel):
    sections: List[WriterSection] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

