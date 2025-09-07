from __future__ import annotations

from typing import List

from investing_agent.schemas.writer_llm import WriterLLMOutput, WriterSection


def _section_exists(markdown: str, title: str) -> bool:
    header = f"## {title}".strip()
    return header in markdown


def _render_section(sec: WriterSection) -> List[str]:
    lines: List[str] = []
    lines.append(f"## {sec.title}")
    lines.append("")
    for p in sec.paragraphs or []:
        lines.append(p.strip())
        lines.append("")
    if sec.refs:
        joined = ";".join([r.strip() for r in sec.refs if r and r.strip()])
        if joined:
            lines.append(f"[ref:{joined}]")
            lines.append("")
    return lines


def merge_llm_sections(base_md: str, out: WriterLLMOutput) -> str:
    """Insert LLM narrative sections between Summary and Per-Year Detail.

    - Idempotent: skips sections already present by title.
    - Deterministic: preserves order from the cassette.
    """
    if not out or not out.sections:
        return base_md
    # Find anchor to insert before Per-Year Detail
    anchor = "## Per-Year Detail"
    idx = base_md.find(anchor)
    if idx == -1:
        # If not found, append at end
        idx = len(base_md)
    # Build insertion text for missing sections only
    to_insert_lines: List[str] = []
    for sec in out.sections:
        if not _section_exists(base_md, sec.title):
            to_insert_lines.extend(_render_section(sec))
    if not to_insert_lines:
        return base_md
    insertion = "\n".join(to_insert_lines).rstrip() + "\n\n"
    return base_md[:idx] + insertion + base_md[idx:]

