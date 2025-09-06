from __future__ import annotations

from typing import List

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def check_report(report_md: str, I: InputsI, V: ValuationV) -> List[str]:
    """
    Simple deterministic checks for analyst-grade hygiene:
    - No TODOs in text
    - Summary numbers present and match formatting
    - Required sections exist: Per-Year Detail, Terminal Value
    - Citations section exists and contains at least one item (when provenance is present)
    """
    issues: List[str] = []
    if "TODO" in report_md:
        issues.append("Report contains TODO placeholder text")
    # Check key numbers exist
    expected = [
        f"{V.value_per_share:,.2f}",
        f"{V.equity_value:,.0f}",
        f"{V.pv_explicit:,.0f}",
        f"{V.pv_terminal:,.0f}",
        f"{V.shares_out:,.0f}",
    ]
    for token in expected:
        if token not in report_md:
            issues.append(f"Missing value in report: {token}")
    # Required sections
    required_sections = ["## Per-Year Detail", "## Terminal Value"]
    for sec in required_sections:
        if sec not in report_md:
            issues.append(f"Missing section: {sec}")
    # Citations coverage: if we have provenance/source, require a citations section
    if I.provenance and (I.provenance.source_url or I.provenance.content_sha256):
        if "## Citations" not in report_md:
            issues.append("Missing Citations section")
        else:
            # Check at least one bullet under citations
            # heuristic: look for a line starting with '- ' after the header
            tail = report_md.split("## Citations", 1)[-1]
            has_bullet = any(line.strip().startswith("-") for line in tail.splitlines())
            if not has_bullet:
                issues.append("Citations section empty")
    return issues
