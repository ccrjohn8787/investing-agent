from __future__ import annotations

from typing import List, Set, Optional, Any, Dict
import re

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle


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


def check_report(
    report_md: str, 
    I: InputsI, 
    V: ValuationV, 
    manifest: Optional[Any] = None,
    evidence_bundle: Optional[EvidenceBundle] = None
) -> List[str]:
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
    # Narrative hygiene: no naked numbers in LLM narrative sections (e.g., Business Model, Thesis, Drivers, Risks, Scenarios, Market vs Value)
    issues.extend(_check_naked_numbers_in_narrative(report_md))
    
    # Priority 2 enhanced validation rules
    issues.extend(_check_uncited_qualitative_claims(report_md))
    issues.extend(_check_novel_numbers(report_md, I, V))
    issues.extend(_check_contradictory_claims(report_md))
    if evidence_bundle:
        issues.extend(_check_weak_evidence_citations(report_md, evidence_bundle))
    issues.extend(_check_generic_assertions(report_md, I))
    
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


def _section_blocks(report_md: str) -> dict:
    lines = report_md.splitlines()
    blocks = {}
    current = None
    buf: list[str] = []
    for ln in lines:
        if ln.startswith("## "):
            if current is not None:
                blocks[current] = "\n".join(buf).strip()
            current = ln[3:].strip()
            buf = []
        else:
            if current is not None:
                buf.append(ln)
    if current is not None:
        blocks[current] = "\n".join(buf).strip()
    return blocks


def _check_naked_numbers_in_narrative(report_md: str) -> List[str]:
    narrative_titles = {
        "Business Model",
        "Thesis",
        "Drivers",
        "Risks",
        "Scenarios",
        "Market vs Value",
    }
    blocks = _section_blocks(report_md)
    import re
    issues: List[str] = []
    num_pat = re.compile(r"(?<!\w)(\d[\d,]*\.?\d*)(?!\w)")
    for title, body in blocks.items():
        if title not in narrative_titles:
            continue
        # Scan lines and flag those with numbers not part of ref tokens or table rows
        for ln in body.splitlines():
            if not ln.strip():
                continue
            if ln.strip().startswith("|"):
                continue
            if "[ref:" in ln:
                # allowed numbers inside ref token only; strip token for scan
                ln = re.sub(r"\[ref:.*?\]", "", ln)
            # ignore bracketed URLs
            ln = re.sub(r"\(https?://[^\)]+\)", "", ln)
            if num_pat.search(ln):
                issues.append(f"Naked number in narrative: {title}")
                break
    return issues


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


# Priority 2: Enhanced validation rules for uncited claims, novel numbers, and content quality

def _check_uncited_qualitative_claims(report_md: str) -> List[str]:
    """Detect strategic assertions that lack evidence citations."""
    issues: List[str] = []
    
    # Strategic narrative sections that require evidence citations
    narrative_sections = {
        "Industry Context & Market Dynamics",
        "Strategic Positioning Analysis", 
        "Financial Performance Review",
        "Forward-Looking Strategic Outlook",
        "Investment Thesis Development",
        "Risk Factor Analysis"
    }
    
    blocks = _section_blocks(report_md)
    
    # Patterns that indicate strategic assertions requiring evidence
    strategic_claim_patterns = [
        r'\b(?:demonstrates?|reveals?|indicates?|suggests?)\b[^\[]*?(?:\.|$)',
        r'\b(?:strong|competitive|sustainable|significant)\s+(?:advantage|position|growth|performance)\b[^\[]*?(?:\.|$)',
        r'\b(?:market\s+(?:leadership|share|expansion)|competitive\s+(?:advantage|moat|position))\b[^\[]*?(?:\.|$)',
        r'\b(?:outperform|superior|leading|dominant)\s+(?:position|performance|execution)\b[^\[]*?(?:\.|$)',
        r'\b(?:growth\s+(?:opportunity|catalyst|driver)|expansion\s+(?:plan|strategy))\b[^\[]*?(?:\.|$)'
    ]
    
    for title, content in blocks.items():
        if title not in narrative_sections:
            continue
            
        # Split into sentences for granular validation
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:  # Skip very short fragments
                continue
                
            # Check if sentence contains strategic claims
            has_strategic_claim = False
            for pattern in strategic_claim_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    has_strategic_claim = True
                    break
            
            if has_strategic_claim:
                # Check if sentence contains evidence citation
                if not re.search(r'\[ev:[^\]]+\]', sentence):
                    issues.append(f"Uncited strategic claim in {title}: '{sentence[:80]}...'")
    
    return issues


def _check_novel_numbers(report_md: str, I: InputsI, V: ValuationV) -> List[str]:
    """Detect quantitative claims not present in InputsI or ValuationV objects."""
    issues: List[str] = []
    
    # Extract all allowed numbers from InputsI and ValuationV
    allowed_numbers = set()
    
    # From ValuationV
    for field_name, field_value in V.model_dump().items():
        if isinstance(field_value, (int, float)):
            # Add formatted versions
            allowed_numbers.add(f"{field_value:,.2f}")
            allowed_numbers.add(f"{field_value:,.0f}")
            allowed_numbers.add(f"{field_value:.2f}")
            allowed_numbers.add(f"{field_value:.0f}")
            
    # From InputsI - key financial metrics
    inputs_dict = I.model_dump()
    for field_name, field_value in inputs_dict.items():
        if isinstance(field_value, (int, float)):
            allowed_numbers.add(f"{field_value:,.2f}")
            allowed_numbers.add(f"{field_value:,.0f}")
            allowed_numbers.add(f"{field_value:.2f}")
            allowed_numbers.add(f"{field_value:.0f}")
    
    # Extract driver arrays from InputsI
    if hasattr(I, 'drivers') and I.drivers:
        for attr_name in ['sales_growth', 'operating_margin', 'wacc', 's2c_ratio']:
            if hasattr(I.drivers, attr_name):
                values = getattr(I.drivers, attr_name)
                if isinstance(values, list):
                    for val in values:
                        if isinstance(val, (int, float)):
                            allowed_numbers.add(f"{val:.1%}")
                            allowed_numbers.add(f"{val:.2%}")
                            allowed_numbers.add(f"{val*100:.1f}")
                            allowed_numbers.add(f"{val*100:.0f}")
    
    # Find numbers in narrative sections
    narrative_sections = {
        "Industry Context & Market Dynamics",
        "Strategic Positioning Analysis", 
        "Financial Performance Review",
        "Forward-Looking Strategic Outlook",
        "Investment Thesis Development",
        "Risk Factor Analysis"
    }
    
    blocks = _section_blocks(report_md)
    number_pattern = re.compile(r'(?<![\w$])([0-9,]+\.?[0-9]*%?)(?![\w.])')
    
    for title, content in blocks.items():
        if title not in narrative_sections:
            continue
            
        # Find all numbers in content
        for match in number_pattern.finditer(content):
            number_str = match.group(1)
            
            # Skip if within a reference token
            start_pos = match.start()
            preceding_text = content[max(0, start_pos-20):start_pos]
            following_text = content[start_pos:min(len(content), start_pos+20)]
            
            if '[ref:' in preceding_text and ']' in following_text:
                continue
                
            # Check if number is allowed
            if number_str not in allowed_numbers:
                # Try common formatting variations
                clean_number = number_str.replace(',', '')
                if (clean_number not in allowed_numbers and 
                    number_str not in ["2024", "2025", "2026", "2027", "2028"] and  # Common years
                    not re.match(r'^[0-9]{1,2}$', clean_number)):  # Single/double digits (common percentages)
                    context = content[max(0, start_pos-40):start_pos+40]
                    issues.append(f"Novel number '{number_str}' in {title}: ...{context}...")
    
    return issues


def _check_contradictory_claims(report_md: str) -> List[str]:
    """Detect potentially contradictory statements within the same report."""
    issues: List[str] = []
    
    # Define opposing concept pairs
    contradiction_patterns = [
        ([r'\bstrong\s+(?:growth|expansion)\b', r'\bgrowing\s+rapidly\b'], 
         [r'\bslowing\s+growth\b', r'\bdeclining\s+(?:growth|performance)\b']),
        ([r'\bcompetitive\s+advantage\b', r'\bmarket\s+leadership\b'], 
         [r'\bintense\s+competition\b', r'\blosing\s+market\s+share\b']),
        ([r'\bstrong\s+margins\b', r'\bmargin\s+expansion\b'], 
         [r'\bmargin\s+pressure\b', r'\bcompressed\s+margins\b']),
        ([r'\blow\s+risk\b', r'\bdefensive\s+characteristics\b'], 
         [r'\bhigh\s+risk\b', r'\bsignificant\s+risks\b']),
    ]
    
    # Check each contradiction pattern
    for positive_patterns, negative_patterns in contradiction_patterns:
        positive_found = []
        negative_found = []
        
        # Find positive claims
        for pattern in positive_patterns:
            matches = re.finditer(pattern, report_md, re.IGNORECASE)
            for match in matches:
                context_start = max(0, match.start() - 50)
                context_end = min(len(report_md), match.end() + 50)
                positive_found.append(report_md[context_start:context_end])
        
        # Find negative claims
        for pattern in negative_patterns:
            matches = re.finditer(pattern, report_md, re.IGNORECASE)
            for match in matches:
                context_start = max(0, match.start() - 50)
                context_end = min(len(report_md), match.end() + 50)
                negative_found.append(report_md[context_start:context_end])
        
        # Report contradictions if both found
        if positive_found and negative_found:
            issues.append(
                f"Contradictory claims detected: positive='{positive_found[0][:60]}...' vs negative='{negative_found[0][:60]}...'"
            )
    
    return issues


def _check_weak_evidence_citations(report_md: str, evidence_bundle: EvidenceBundle) -> List[str]:
    """Check for citations to low-confidence evidence items."""
    issues: List[str] = []
    
    if not evidence_bundle or not evidence_bundle.items:
        return issues
    
    # Build evidence confidence map
    evidence_confidence = {}
    for item in evidence_bundle.items:
        if item.claims:
            avg_confidence = sum(claim.confidence for claim in item.claims) / len(item.claims)
            evidence_confidence[item.id] = avg_confidence
    
    # Find evidence citations in report
    citation_pattern = re.compile(r'\[ev:([^\]]+)\]')
    
    for match in citation_pattern.finditer(report_md):
        evidence_id = match.group(1)
        
        if evidence_id in evidence_confidence:
            confidence = evidence_confidence[evidence_id]
            
            # Flag low-confidence evidence (below 0.70) used for material claims
            if confidence < 0.70:
                context_start = max(0, match.start() - 60)
                context_end = min(len(report_md), match.end() + 60)
                context = report_md[context_start:context_end]
                
                issues.append(
                    f"Low-confidence evidence citation (conf={confidence:.2f}): {evidence_id} in context '...{context}...'"
                )
    
    return issues


def _check_generic_assertions(report_md: str, I: InputsI) -> List[str]:
    """Detect generic claims that could apply to any company in the sector."""
    issues: List[str] = []
    
    # Generic phrases that lack company specificity
    generic_patterns = [
        r'\b(?:well-positioned|strong\s+position)\s+in\s+the\s+(?:industry|market)\b',
        r'\bbenefits?\s+from\s+(?:industry|market)\s+(?:trends?|dynamics?)\b',
        r'\b(?:established|leading)\s+(?:player|company)\s+in\s+the\s+(?:industry|sector)\b',
        r'\boperates?\s+in\s+a\s+(?:growing|dynamic)\s+(?:market|industry)\b',
        r'\bhas\s+(?:strong|competitive)\s+(?:fundamentals?|position)\b',
        r'\bexpected\s+to\s+(?:benefit|grow)\s+from\s+(?:industry|market)\s+(?:growth|trends?)\b'
    ]
    
    company_name = getattr(I, 'company', 'Company') if hasattr(I, 'company') else 'Company'
    company_ticker = getattr(I, 'ticker', 'TICKER') if hasattr(I, 'ticker') else 'TICKER'
    
    # Check narrative sections for generic assertions
    narrative_sections = {
        "Industry Context & Market Dynamics",
        "Strategic Positioning Analysis", 
        "Investment Thesis Development"
    }
    
    blocks = _section_blocks(report_md)
    
    for title, content in blocks.items():
        if title not in narrative_sections:
            continue
            
        for pattern in generic_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                sentence_start = content.rfind('.', 0, match.start()) + 1
                sentence_end = content.find('.', match.end())
                if sentence_end == -1:
                    sentence_end = len(content)
                
                sentence = content[sentence_start:sentence_end].strip()
                
                # Check if sentence mentions company name or ticker
                if (company_name.lower() not in sentence.lower() and 
                    company_ticker.lower() not in sentence.lower()):
                    issues.append(
                        f"Generic assertion in {title}: '{sentence[:80]}...' (lacks company-specific details)"
                    )
    
    return issues
