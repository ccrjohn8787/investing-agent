from __future__ import annotations

from typing import List

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def check_report(report_md: str, I: InputsI, V: ValuationV) -> List[str]:
    """Simple deterministic checks: presence of key numbers and no TODOs."""
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
    return issues

