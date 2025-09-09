from __future__ import annotations

import re
from typing import List, Set, Tuple, Optional, Dict, Any
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle


class WriterValidationError(Exception):
    """Raised when writer output contains prohibited content."""
    pass


class WriterValidator:
    """Validates writer output to ensure read-only compliance and citation discipline."""
    
    def __init__(self, inputs: InputsI, valuation: ValuationV, evidence_context: Optional[Dict[str, Any]] = None, evidence_bundle: Optional[EvidenceBundle] = None, require_evidence_citations: bool = True):
        """Initialize validator with known numeric values and evidence context.
        
        Args:
            inputs: InputsI object containing all driver and assumption values
            valuation: ValuationV object containing all computed valuation results
            evidence_context: Optional evidence context for citation validation (deprecated, use evidence_bundle)
            evidence_bundle: Optional EvidenceBundle for proper evidence validation
            require_evidence_citations: If False, skip evidence citation validation (for transition period)
        """
        self.inputs = inputs
        self.valuation = valuation
        self.evidence_context = evidence_context or {}
        self.evidence_bundle = evidence_bundle
        self.require_evidence_citations = require_evidence_citations
        
        # Build allowed evidence IDs from evidence bundle
        self.allowed_evidence_ids: Set[str] = set()
        if self.evidence_bundle:
            self.allowed_evidence_ids = {item.id for item in self.evidence_bundle.items}
        
        self._build_allowed_numbers()
    
    def _build_allowed_numbers(self) -> None:
        """Build comprehensive set of allowed numeric values from inputs and valuation."""
        self.allowed_numbers: Set[str] = set()
        
        # Extract numbers from InputsI
        self._extract_numbers_from_dict(self.inputs.model_dump(), "inputs")
        
        # Extract numbers from ValuationV  
        self._extract_numbers_from_dict(self.valuation.model_dump(), "valuation")
        
        # Common financial formatting variations
        self._add_formatting_variants()
    
    def _extract_numbers_from_dict(self, data: Dict[str, Any], prefix: str = "") -> None:
        """Recursively extract numeric values from nested dictionaries."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    # Store multiple representations
                    self.allowed_numbers.add(str(value))
                    self.allowed_numbers.add(f"{value:.2f}")
                    if value >= 1000:
                        # Add comma-separated format
                        self.allowed_numbers.add(f"{value:,.0f}")
                        self.allowed_numbers.add(f"{value:,.2f}")
                    if isinstance(value, float) and 0 < value < 1:
                        # Add percentage format
                        self.allowed_numbers.add(f"{value*100:.1f}%")
                        self.allowed_numbers.add(f"{value*100:.2f}%")
                elif isinstance(value, dict):
                    self._extract_numbers_from_dict(value, prefix)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, (int, float)):
                            self.allowed_numbers.add(str(item))
                        elif isinstance(item, dict):
                            self._extract_numbers_from_dict(item, prefix)
                        elif isinstance(item, list):
                            for subitem in item:
                                if isinstance(subitem, (int, float)):
                                    self.allowed_numbers.add(str(subitem))
                                elif isinstance(subitem, dict):
                                    self._extract_numbers_from_dict(subitem, prefix)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (int, float)):
                    self.allowed_numbers.add(str(item))
                elif isinstance(item, (dict, list)):
                    self._extract_numbers_from_dict(item, prefix)
    
    def _add_formatting_variants(self) -> None:
        """Add common formatting variants for financial numbers."""
        new_numbers = set()
        for num_str in list(self.allowed_numbers):
            try:
                num = float(num_str.replace(',', '').replace('%', ''))
                # Add billions/millions format
                if num >= 1_000_000_000:
                    new_numbers.add(f"{num/1_000_000_000:.1f}B")
                    new_numbers.add(f"{num/1_000_000_000:.2f}B")
                elif num >= 1_000_000:
                    new_numbers.add(f"{num/1_000_000:.1f}M")
                    new_numbers.add(f"{num/1_000_000:.2f}M")
            except ValueError:
                continue
        
        self.allowed_numbers.update(new_numbers)
    
    def validate_numeric_content(self, content: str) -> List[str]:
        """Validate that all numeric content in text is from allowed sources.
        
        Args:
            content: Text content to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Extract all numeric patterns from content
        numeric_patterns = self._extract_numeric_patterns(content)
        
        # Check each number against allowed set
        for pattern_match, line_num in numeric_patterns:
            if not self._is_allowed_citation_context(pattern_match, content):
                # Check if number is in allowed set
                cleaned_number = self._clean_numeric_pattern(pattern_match)
                if cleaned_number not in self.allowed_numbers:
                    errors.append(
                        f"Line {line_num}: Novel numeric value '{pattern_match}' not found in InputsI/ValuationV. "
                        f"Use [ref:computed:field] citation instead."
                    )
        
        return errors
    
    def _extract_numeric_patterns(self, content: str) -> List[Tuple[str, int]]:
        """Extract all numeric patterns from content with line numbers."""
        patterns = []
        
        # Comprehensive numeric patterns
        numeric_regex = re.compile(
            r'\b(?:'
            r'\$?[\d,]+(?:\.\d+)?[BMK]?'  # Currency and scale ($1.2B, 150M, etc.)
            r'|\d+(?:\.\d+)?%'  # Percentages (15.5%, 3%)
            r'|\d+(?:\.\d+)?x'  # Multiples (2.5x, 10x)
            r'|\d{1,3}(?:,\d{3})*(?:\.\d+)?'  # Comma-separated numbers
            r'|\d+(?:\.\d+)?'  # Basic numbers
            r')\b',
            re.IGNORECASE
        )
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Skip lines with citations (they're referencing allowed values)
            if '[ref:' in line:
                continue
                
            for match in numeric_regex.finditer(line):
                patterns.append((match.group(), line_num))
        
        return patterns
    
    def _clean_numeric_pattern(self, pattern: str) -> str:
        """Clean numeric pattern for comparison with allowed numbers."""
        # Remove currency symbols, convert scale indicators
        cleaned = pattern.replace('$', '').replace(',', '')
        
        if cleaned.endswith('B'):
            base = float(cleaned[:-1]) * 1_000_000_000
            return str(int(base) if base.is_integer() else base)
        elif cleaned.endswith('M'):
            base = float(cleaned[:-1]) * 1_000_000
            return str(int(base) if base.is_integer() else base)
        elif cleaned.endswith('K'):
            base = float(cleaned[:-1]) * 1_000
            return str(int(base) if base.is_integer() else base)
        elif cleaned.endswith('x'):
            return cleaned[:-1]
        
        return cleaned
    
    def _is_allowed_citation_context(self, pattern: str, content: str) -> bool:
        """Check if numeric pattern appears in allowed citation context."""
        # Look for patterns like [ref:computed:valuation.value_per_share] followed by number
        citation_context_regex = re.compile(
            r'\[ref:(?:computed:|table:|snap:)[^\]]+\][\s\-]*' + re.escape(pattern),
            re.IGNORECASE
        )
        
        return bool(citation_context_regex.search(content))
    
    def validate_citation_coverage(self, content: str) -> List[str]:
        """Validate that qualitative claims have proper evidence citations.
        
        Args:
            content: Text content to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        if not self.require_evidence_citations:
            return []
            
        errors = []
        
        # Patterns that indicate strategic/qualitative claims requiring evidence
        claim_patterns = [
            r'\b(?:expects?|projects?|forecasts?|anticipates?|estimates?)\b',
            r'\b(?:strong|weak|positive|negative|growth|decline|improvement|deterioration)\b',
            r'\b(?:competitive|market share|industry|sector|peers?)\b',
            r'\b(?:strategy|strategic|expansion|investment|initiative)\b',
            r'\b(?:risk|opportunity|threat|advantage|strength|weakness)\b',
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Skip markdown headers and references
            if line.strip().startswith('#') or '[ref:' in line:
                continue
            
            # Check if line contains strategic claims
            has_strategic_claim = any(
                re.search(pattern, line, re.IGNORECASE) for pattern in claim_patterns
            )
            
            if has_strategic_claim:
                # Check for evidence citation
                ev_citations = re.findall(r'\[ev:([^\]]+)\]', line)
                if not ev_citations:
                    errors.append(
                        f"Line {line_num}: Strategic claim lacks evidence citation [ev:evidence_id]. "
                        f"Content: '{line.strip()[:80]}...'"
                    )
                else:
                    # Validate evidence IDs if evidence bundle is available
                    if self.evidence_bundle:
                        for ev_id in ev_citations:
                            if ev_id not in self.allowed_evidence_ids:
                                errors.append(
                                    f"Line {line_num}: Invalid evidence ID '{ev_id}' in citation [ev:{ev_id}]. "
                                    f"Available evidence IDs: {sorted(list(self.allowed_evidence_ids))[:5]}{'...' if len(self.allowed_evidence_ids) > 5 else ''}"
                                )
        
        return errors
    
    def validate_evidence_citation_quality(self, content: str) -> List[str]:
        """Validate that evidence citations use high-confidence claims appropriately.
        
        Args:
            content: Text content to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[str] = []
        
        if not self.evidence_bundle or not self.require_evidence_citations:
            return errors
        
        # Extract all evidence citations
        ev_citations = re.findall(r'\[ev:([^\]]+)\]', content)
        
        for ev_id in ev_citations:
            # Find corresponding evidence item
            evidence_item = None
            for item in self.evidence_bundle.items:
                if item.id == ev_id:
                    evidence_item = item
                    break
            
            if not evidence_item:
                continue  # Already handled in validate_citation_coverage
            
            # Check if evidence has high-confidence claims
            high_conf_claims = [claim for claim in evidence_item.claims if claim.confidence >= 0.80]
            
            if not high_conf_claims:
                errors.append(
                    f"Evidence citation [ev:{ev_id}] uses low-confidence evidence. "
                    f"Best confidence: {max([c.confidence for c in evidence_item.claims], default=0.0):.2f}"
                )
        
        return errors
    
    def validate_section_content(self, sections: List[Dict[str, Any]]) -> List[str]:
        """Validate entire sections for read-only compliance and citations.
        
        Args:
            sections: List of section dictionaries with title and paragraphs
            
        Returns:
            List of validation errors (empty if valid)
        """
        all_errors = []
        
        for section in sections:
            section_title = section.get('title', 'Unknown Section')
            paragraphs = section.get('paragraphs', [])
            
            # Combine all paragraphs for validation
            section_content = '\n'.join(paragraphs)
            
            # Validate numeric content
            numeric_errors = self.validate_numeric_content(section_content)
            for error in numeric_errors:
                all_errors.append(f"[{section_title}] {error}")
            
            # Validate citation coverage
            citation_errors = self.validate_citation_coverage(section_content)
            for error in citation_errors:
                all_errors.append(f"[{section_title}] {error}")
            
            # Validate evidence citation quality
            quality_errors = self.validate_evidence_citation_quality(section_content)
            for error in quality_errors:
                all_errors.append(f"[{section_title}] {error}")
        
        return all_errors
    
    def validate_writer_output(self, writer_output: Dict[str, Any]) -> None:
        """Validate complete writer output and raise exception if invalid.
        
        Args:
            writer_output: Complete writer output dictionary
            
        Raises:
            WriterValidationError: If validation fails
        """
        sections = writer_output.get('sections', [])
        errors = self.validate_section_content(sections)
        
        if errors:
            error_msg = "Writer validation failed:\n" + '\n'.join(f"  - {error}" for error in errors)
            raise WriterValidationError(error_msg)
    
    def get_available_evidence_citations(self) -> Dict[str, Dict[str, Any]]:
        """Get available evidence citations for writer reference.
        
        Returns:
            Dictionary mapping evidence_id to evidence metadata
        """
        if not self.evidence_bundle:
            return {}
        
        citations = {}
        for item in self.evidence_bundle.items:
            # Only include high-confidence evidence
            high_conf_claims = [claim for claim in item.claims if claim.confidence >= 0.80]
            if high_conf_claims:
                citations[item.id] = {
                    'title': item.title,
                    'source_type': item.source_type,
                    'date': item.date,
                    'claims': len(high_conf_claims),
                    'confidence_range': [
                        round(min(c.confidence for c in high_conf_claims), 2),
                        round(max(c.confidence for c in high_conf_claims), 2)
                    ],
                    'drivers_covered': list(set(c.driver for c in high_conf_claims))
                }
        
        return citations
    
    def suggest_evidence_citations(self, claim_text: str, driver_hint: Optional[str] = None) -> List[str]:
        """Suggest appropriate evidence citations for a given claim.
        
        Args:
            claim_text: Text of the claim needing evidence
            driver_hint: Optional hint about which driver is relevant (growth, margin, wacc, s2c)
            
        Returns:
            List of suggested evidence IDs
        """
        if not self.evidence_bundle:
            return []
        
        suggestions = []
        claim_lower = claim_text.lower()
        
        # Keywords that might indicate relevance
        growth_keywords = ['growth', 'revenue', 'sales', 'expansion', 'market share']
        margin_keywords = ['margin', 'profitability', 'cost', 'efficiency', 'pricing']
        wacc_keywords = ['capital', 'cost of capital', 'risk', 'debt', 'financing']
        s2c_keywords = ['investment', 'capital expenditure', 'capex', 'asset utilization']
        
        for item in self.evidence_bundle.items:
            # Only suggest high-confidence evidence
            high_conf_claims = [claim for claim in item.claims if claim.confidence >= 0.80]
            if not high_conf_claims:
                continue
            
            # Check driver hint first
            if driver_hint:
                if any(claim.driver == driver_hint for claim in high_conf_claims):
                    suggestions.append(item.id)
                    continue
            
            # Check keyword matching
            title_lower = item.title.lower()
            relevance_score = 0
            
            # Check growth-related content
            if any(keyword in claim_lower or keyword in title_lower for keyword in growth_keywords):
                if any(claim.driver == 'growth' for claim in high_conf_claims):
                    relevance_score += 1
            
            # Check margin-related content  
            if any(keyword in claim_lower or keyword in title_lower for keyword in margin_keywords):
                if any(claim.driver == 'margin' for claim in high_conf_claims):
                    relevance_score += 1
            
            # Add other keyword checks...
            if relevance_score > 0:
                suggestions.append(item.id)
        
        # Return top 3 suggestions
        return suggestions[:3]