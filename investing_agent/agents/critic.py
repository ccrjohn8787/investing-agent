from __future__ import annotations

from typing import List, Set, Optional, Any
import re

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


def _extract_ref_tokens(report_md: str) -> List[str]:
    """Parse inline reference tokens of the form [ref:token1;token2]."""
    tokens: List[str] = []
    i = 0
    while True:
        start = report_md.find("[ref:", i)
        if start == -1:
            break
        end = report_md.find("]", start)
        if end == -1:
            break
        body = report_md[start + 5 : end]  # after '[ref:' up to ']'
        parts = [p.strip() for p in body.split(";") if p.strip()]
        tokens.extend(parts)
        i = end + 1
    return tokens


def _resolve_tokens(tokens: List[str], report_md: str, known_snap_shas: Set[str]) -> List[str]:
    """Return a list of issues for tokens that fail to resolve."""
    issues: List[str] = []
    # Known computed keys for now
    known_computed = {
        "valuation.value_per_share",
        "valuation.equity_value",
        "valuation.pv_explicit",
        "valuation.pv_terminal",
        "valuation.shares_out",
    }
    for t in tokens:
        if t.startswith("table:") or t.startswith("section:"):
            name = t.split(":", 1)[1].strip()
            header = f"## {name}"
            if header not in report_md:
                issues.append(f"Unresolved reference: {t} (missing section '{header}')")
        elif t.startswith("snap:"):
            sha = t.split(":", 1)[1].strip()
            if not sha or sha not in known_snap_shas:
                issues.append(f"Unresolved reference: {t} (unknown snapshot sha)")
        elif t.startswith("computed:"):
            key = t.split(":", 1)[1].strip()
            if key not in known_computed:
                issues.append(f"Unresolved reference: {t} (unknown computed key)")
        else:
            issues.append(f"Unknown reference type: {t}")
    return issues


def check_report(report_md: str, I: InputsI, V: ValuationV, manifest: Optional[Any] = None) -> List[str]:
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
    # Reference tokens resolve
    ref_tokens = _extract_ref_tokens(report_md)
    known_shas: Set[str] = set()
    if I.provenance and I.provenance.content_sha256:
        known_shas.add(I.provenance.content_sha256)
    # Also accept snapshot SHAs from an optional manifest
    try:
        if manifest and getattr(manifest, "snapshots", None):
            for s in manifest.snapshots:
                sha = getattr(s, "content_sha256", None)
                if sha:
                    known_shas.add(sha)
    except Exception:
        pass
    ref_issues = _resolve_tokens(ref_tokens, report_md, known_shas)
    issues.extend(ref_issues)
    # Arithmetic consistency checks with lenient tolerance (rounding in tables)
    issues.extend(_check_arithmetic_consistency(report_md, I, V, rel_tol=0.02))
    return issues


def _num(s: str) -> Optional[float]:
    s = s.strip()
    if not s:
        return None
    s = s.replace(",", "")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return None


def _extract_summary_value(report_md: str, label: str) -> Optional[float]:
    pat = re.compile(rf"^-\s*{re.escape(label)}:\s*([0-9,\.]+)", re.IGNORECASE | re.MULTILINE)
    m = pat.search(report_md)
    if not m:
        return None
    return _num(m.group(1))


def _extract_terminal_pv(report_md: str) -> Optional[float]:
    pat = re.compile(r"^-\s*PV\(TV\):\s*([0-9,\.]+)", re.IGNORECASE | re.MULTILINE)
    m = pat.search(report_md)
    if not m:
        return None
    return _num(m.group(1))


def _sum_pv_fcff_from_table(report_md: str) -> Optional[float]:
    # Locate Per-Year Detail table and sum the PV(FCFF) column
    if "## Per-Year Detail" not in report_md:
        return None
    tail = report_md.split("## Per-Year Detail", 1)[-1]
    lines = [ln.strip() for ln in tail.splitlines()]
    # Find header row and separator row
    hdr_idx = None
    for i, ln in enumerate(lines[:50]):
        if ln.startswith("|") and "PV(FCFF)" in ln:
            hdr_idx = i
            break
    if hdr_idx is None:
        return None
    headers = [h.strip() for h in lines[hdr_idx].strip("|").split("|")]
    try:
        pv_idx = headers.index("PV(FCFF)")
    except ValueError:
        return None
    # Data rows start after the separator line (hdr_idx+1)
    total = 0.0
    for ln in lines[hdr_idx + 2 : hdr_idx + 2 + 100]:
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) <= pv_idx:
            continue
        v = _num(cells[pv_idx])
        if v is not None:
            total += v
    return total


def _check_arithmetic_consistency(report_md: str, I: InputsI, V: ValuationV, rel_tol: float = 0.02) -> List[str]:
    issues: List[str] = []
    # PV explicit vs sum of table
    pv_exp_summary = _extract_summary_value(report_md, "PV (explicit)")
    pv_exp_table = _sum_pv_fcff_from_table(report_md)
    if pv_exp_summary is not None and pv_exp_table is not None and pv_exp_summary > 0:
        if abs(pv_exp_summary - pv_exp_table) / pv_exp_summary > rel_tol:
            issues.append(
                f"Inconsistent PV explicit: summary={pv_exp_summary:,.0f} vs table sum={pv_exp_table:,.0f}"
            )
    # PV terminal vs PV(TV)
    pv_term_summary = _extract_summary_value(report_md, "PV (terminal)")
    pv_term_terminal = _extract_terminal_pv(report_md)
    if pv_term_summary is not None and pv_term_terminal is not None and pv_term_summary > 0:
        if abs(pv_term_summary - pv_term_terminal) / pv_term_summary > rel_tol:
            issues.append(
                f"Inconsistent PV terminal: summary={pv_term_summary:,.0f} vs terminal={pv_term_terminal:,.0f}"
            )
    # Equity value internal bridge check (using I for net debt & cash)
    eq = _extract_summary_value(report_md, "Equity value")
    if eq is not None and pv_exp_summary is not None and pv_term_summary is not None:
        pv_ops = pv_exp_summary + pv_term_summary
        equity_calc = pv_ops - float(I.net_debt) + float(I.cash_nonop)
        if eq > 0 and abs(eq - equity_calc) / eq > (rel_tol * 2):
            issues.append(
                f"Equity value check failed: summary={eq:,.0f} vs calc={equity_calc:,.0f}"
            )
    return issues
