from __future__ import annotations

from typing import List, Optional

from investing_agent.schemas.writer_llm import WriterLLMOutput, WriterSection
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.agents.writer_validation import WriterValidator, WriterValidationError


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


def validate_writer_output(out: WriterLLMOutput, inputs: InputsI, valuation: ValuationV) -> None:
    """Validate WriterLLMOutput for read-only compliance and citation discipline.
    
    Args:
        out: WriterLLMOutput to validate
        inputs: InputsI containing allowed numeric values
        valuation: ValuationV containing allowed numeric values
        
    Raises:
        WriterValidationError: If validation fails
    """
    if not out or not out.sections:
        return
    
    validator = WriterValidator(inputs, valuation, require_evidence_citations=False)
    
    # Convert WriterLLMOutput sections to dict format for validation
    sections_dict = []
    for section in out.sections:
        sections_dict.append({
            'title': section.title,
            'paragraphs': section.paragraphs or []
        })
    
    # Validate sections
    errors = validator.validate_section_content(sections_dict)
    
    if errors:
        error_msg = "Writer validation failed:\n" + '\n'.join(f"  - {error}" for error in errors)
        raise WriterValidationError(error_msg)


def merge_llm_sections(base_md: str, out: WriterLLMOutput, inputs: Optional[InputsI] = None, valuation: Optional[ValuationV] = None) -> str:
    """Insert LLM narrative sections between Summary and Per-Year Detail.

    - Idempotent: skips sections already present by title.
    - Deterministic: preserves order from the cassette.
    - Validates: ensures read-only compliance when inputs/valuation provided.
    
    Args:
        base_md: Base markdown content
        out: WriterLLMOutput containing sections to merge
        inputs: Optional InputsI for validation
        valuation: Optional ValuationV for validation
        
    Returns:
        Updated markdown with merged sections
        
    Raises:
        WriterValidationError: If validation fails when inputs/valuation provided
    """
    if not out or not out.sections:
        return base_md
    
    # Validate if inputs and valuation are provided
    if inputs is not None and valuation is not None:
        validate_writer_output(out, inputs, valuation)
    
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

