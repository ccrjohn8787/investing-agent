from __future__ import annotations

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class WriterSection(BaseModel):
    title: str
    paragraphs: List[str] = Field(default_factory=list)
    refs: List[str] = Field(default_factory=list)


class WriterLLMOutput(BaseModel):
    """
    Contract for LLM-generated narrative sections.

    Constraints:
    - No new numbers; paragraphs may include [ref:computed:...], [table:...], [section:...], [snap:<sha>].
    - Citations list carries external references; Critic verifies coverage.
    - models metadata (optional) records deterministic settings for provenance.
    """

    sections: List[WriterSection] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    models: Optional[Dict[str, Any]] = None

