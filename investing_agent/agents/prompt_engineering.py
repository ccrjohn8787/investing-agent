from __future__ import annotations

"""
Professional Prompt Engineering System

Dynamic prompt loading and context injection for professional investment analysis.
Manages specialized prompts for each section type with evidence integration and
quality validation for institutional-grade report generation.
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import re
from dataclasses import dataclass, field
from datetime import datetime

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
from investing_agent.schemas.writer_professional import SectionType

@dataclass
class PromptContext:
    """Context data for prompt engineering."""
    company_name: str
    ticker: str
    industry_sector: str
    market_cap: Optional[float] = None
    current_price: Optional[float] = None
    recommendation: str = "HOLD"
    time_horizon: int = 12  # months
    expected_return: Optional[float] = None
    
    # Valuation metrics
    value_per_share: float = 0.0
    equity_value: float = 0.0
    pv_explicit: float = 0.0
    pv_terminal: float = 0.0
    tax_rate: float = 0.0
    
    # Context summaries
    industry_position: str = ""
    competitive_moats: str = ""
    growth_catalysts: str = ""
    primary_risks: str = ""
    
    # Evidence summary
    evidence_summary: str = ""
    evidence_coverage: float = 0.0
    citation_density: float = 0.0
    meets_standards: bool = False

@dataclass
class PromptTemplate:
    """Professional prompt template with metadata."""
    section_type: SectionType
    template_content: str
    required_evidence_types: List[str] = field(default_factory=list)
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    output_structure: Dict[str, str] = field(default_factory=dict)
    
class PromptEngineeringManager:
    """Manages professional prompt templates and context injection."""
    
    def __init__(self, prompts_base_dir: Optional[Path] = None):
        """Initialize prompt engineering manager.
        
        Args:
            prompts_base_dir: Base directory for prompt templates
        """
        self.prompts_base_dir = prompts_base_dir or Path("prompts/writer")
        self.templates: Dict[SectionType, PromptTemplate] = {}
        self.context: Optional[PromptContext] = None
        
        # Load all prompt templates
        self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> None:
        """Load all professional prompt templates from files."""
        template_mappings = {
            "Industry Context & Market Dynamics": "industry_analysis.md",
            "Strategic Positioning Analysis": "competitive_positioning.md",
            "Financial Performance Review": "financial_performance.md",
            "Forward-Looking Strategic Outlook": "financial_performance.md",  # Reuse financial for now
            "Investment Thesis Development": "investment_thesis.md",
            "Risk Factor Analysis": "risk_assessment.md"
        }
        
        for section_type, filename in template_mappings.items():
            template_path = self.prompts_base_dir / filename
            if template_path.exists():
                template_content = template_path.read_text()
                
                # Extract metadata from template
                required_evidence = self._extract_evidence_requirements(template_content)
                quality_reqs = self._extract_quality_requirements(template_content)
                
                self.templates[section_type] = PromptTemplate(
                    section_type=section_type,
                    template_content=template_content,
                    required_evidence_types=required_evidence,
                    quality_requirements=quality_reqs
                )
    
    def prepare_context(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence_bundle: Optional[EvidenceBundle] = None,
        recommendation: str = "HOLD",
        expected_return: Optional[float] = None
    ) -> PromptContext:
        """Prepare comprehensive context for prompt engineering.
        
        Args:
            inputs: InputsI containing company and valuation inputs
            valuation: ValuationV containing computed valuation results
            evidence_bundle: Optional evidence bundle for citations
            recommendation: Investment recommendation (BUY/HOLD/SELL)
            expected_return: Expected return percentage
            
        Returns:
            Complete prompt context
        """
        # Create evidence summary
        evidence_summary = ""
        evidence_coverage = 0.0
        if evidence_bundle:
            evidence_summary = self._create_evidence_summary(evidence_bundle)
            high_conf_claims = evidence_bundle.get_high_confidence_claims(0.80)
            evidence_coverage = len(high_conf_claims) / max(len(evidence_bundle.items), 1)
        
        # Extract basic company information
        company_name = inputs.company or "Target Company"
        ticker = inputs.ticker or "TICKER"
        
        # Create context
        context = PromptContext(
            company_name=company_name,
            ticker=ticker,
            industry_sector=self._infer_industry_sector(inputs, evidence_bundle),
            recommendation=recommendation,
            expected_return=expected_return,
            
            # Valuation metrics
            value_per_share=float(valuation.value_per_share),
            equity_value=float(valuation.equity_value),
            pv_explicit=float(valuation.pv_explicit),
            pv_terminal=float(valuation.pv_terminal),
            tax_rate=float(inputs.tax_rate),
            
            # Context summaries
            industry_position=self._create_industry_summary(evidence_bundle),
            competitive_moats=self._create_competitive_summary(evidence_bundle),
            growth_catalysts=self._create_growth_summary(inputs, evidence_bundle),
            primary_risks=self._create_risk_summary(evidence_bundle),
            
            # Evidence context
            evidence_summary=evidence_summary,
            evidence_coverage=evidence_coverage,
            meets_standards=evidence_coverage >= 0.80
        )
        
        self.context = context
        return context
    
    def generate_section_prompt(
        self,
        section_type: SectionType,
        context: Optional[PromptContext] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate specialized prompt for section type.
        
        Args:
            section_type: Type of section to generate prompt for
            context: Prompt context (uses prepared context if None)
            additional_context: Additional context variables
            
        Returns:
            Complete prompt with context injection
        """
        if section_type not in self.templates:
            raise ValueError(f"No template found for section type: {section_type}")
        
        template = self.templates[section_type]
        prompt_context = context or self.context
        
        if not prompt_context:
            raise ValueError("No prompt context available. Call prepare_context() first.")
        
        # Create context dictionary for template substitution
        context_vars = {
            'company_name': prompt_context.company_name,
            'ticker': prompt_context.ticker,
            'industry_sector': prompt_context.industry_sector,
            'market_cap': prompt_context.market_cap or "N/A",
            'recommendation': prompt_context.recommendation,
            'time_horizon': prompt_context.time_horizon,
            'expected_return': prompt_context.expected_return or "TBD",
            
            # Valuation context
            'value_per_share': prompt_context.value_per_share,
            'equity_value': prompt_context.equity_value,
            'pv_explicit': prompt_context.pv_explicit,
            'pv_terminal': prompt_context.pv_terminal,
            'tax_rate': prompt_context.tax_rate,
            
            # Strategic context
            'industry_position': prompt_context.industry_position,
            'competitive_moats': prompt_context.competitive_moats,
            'growth_catalysts': prompt_context.growth_catalysts,
            'primary_risks': prompt_context.primary_risks,
            
            # Evidence context
            'evidence_summary': prompt_context.evidence_summary,
            'evidence_coverage': f"{prompt_context.evidence_coverage:.1%}",
            'meets_standards': "✓" if prompt_context.meets_standards else "✗",
            
            # Additional derived context
            'growth_summary': self._create_growth_context(prompt_context),
            'margin_summary': self._create_margin_context(prompt_context),
            'wacc_summary': self._create_wacc_context(prompt_context),
            'peer_companies': self._get_peer_companies(prompt_context),
            'market_position_summary': self._get_market_position(prompt_context)
        }
        
        # Add any additional context
        if additional_context:
            context_vars.update(additional_context)
        
        # Perform template substitution
        prompt_content = template.template_content
        for key, value in context_vars.items():
            placeholder = "{" + key + "}"
            prompt_content = prompt_content.replace(placeholder, str(value))
        
        return prompt_content
    
    def generate_all_section_prompts(
        self,
        context: Optional[PromptContext] = None
    ) -> Dict[SectionType, str]:
        """Generate prompts for all professional sections.
        
        Args:
            context: Prompt context (uses prepared context if None)
            
        Returns:
            Dictionary mapping section types to specialized prompts
        """
        prompts = {}
        prompt_context = context or self.context
        
        if not prompt_context:
            raise ValueError("No prompt context available. Call prepare_context() first.")
        
        for section_type in self.templates.keys():
            prompts[section_type] = self.generate_section_prompt(section_type, prompt_context)
        
        return prompts
    
    def get_evidence_requirements(self, section_type: SectionType) -> List[str]:
        """Get evidence requirements for specific section type.
        
        Args:
            section_type: Section type to get requirements for
            
        Returns:
            List of required evidence types
        """
        if section_type in self.templates:
            return self.templates[section_type].required_evidence_types
        return []
    
    def validate_prompt_readiness(
        self,
        context: Optional[PromptContext] = None
    ) -> Dict[str, Any]:
        """Validate that prompt system is ready for generation.
        
        Args:
            context: Prompt context to validate
            
        Returns:
            Validation results
        """
        prompt_context = context or self.context
        
        validation_results = {
            "ready": True,
            "templates_loaded": len(self.templates),
            "context_available": prompt_context is not None,
            "issues": []
        }
        
        # Check template availability
        required_sections = [
            "Industry Context & Market Dynamics",
            "Strategic Positioning Analysis",
            "Financial Performance Review",
            "Investment Thesis Development",
            "Risk Factor Analysis"
        ]
        
        missing_templates = [s for s in required_sections if s not in self.templates]
        if missing_templates:
            validation_results["issues"].append(f"Missing templates: {missing_templates}")
            validation_results["ready"] = False
        
        # Check context completeness
        if prompt_context:
            if not prompt_context.company_name or prompt_context.company_name == "Target Company":
                validation_results["issues"].append("Company name not properly set")
            
            if prompt_context.value_per_share <= 0:
                validation_results["issues"].append("Valuation metrics not properly calculated")
            
            if prompt_context.evidence_coverage < 0.5:
                validation_results["issues"].append(f"Low evidence coverage: {prompt_context.evidence_coverage:.1%}")
        else:
            validation_results["issues"].append("No prompt context prepared")
            validation_results["ready"] = False
        
        return validation_results
    
    def _create_evidence_summary(self, evidence_bundle: EvidenceBundle) -> str:
        """Create formatted evidence summary for prompts."""
        if not evidence_bundle or not evidence_bundle.items:
            return "No evidence available for analysis."
        
        summary_lines = []
        summary_lines.append(f"Available Evidence ({len(evidence_bundle.items)} items):")
        
        for item in evidence_bundle.items[:5]:  # Show top 5
            high_conf_claims = [c for c in item.claims if c.confidence >= 0.80]
            if high_conf_claims:
                drivers = list(set(c.driver for c in high_conf_claims))
                conf_range = f"{min(c.confidence for c in high_conf_claims):.2f}-{max(c.confidence for c in high_conf_claims):.2f}"
                summary_lines.append(f"- {item.id}: {item.title}")
                summary_lines.append(f"  Source: {item.source_type}, Drivers: {drivers}, Confidence: {conf_range}")
        
        if len(evidence_bundle.items) > 5:
            summary_lines.append(f"... and {len(evidence_bundle.items) - 5} more evidence items")
        
        return "\n".join(summary_lines)
    
    def _extract_evidence_requirements(self, template_content: str) -> List[str]:
        """Extract evidence requirements from template content."""
        # Look for evidence requirement patterns in template
        evidence_patterns = re.findall(r'evidence[^:]*:\s*\[ev:([^\]]+)\]', template_content, re.IGNORECASE)
        return list(set(evidence_patterns))
    
    def _extract_quality_requirements(self, template_content: str) -> Dict[str, Any]:
        """Extract quality requirements from template content."""
        quality_reqs = {}
        
        # Look for citation requirements
        if "minimum 2-3 evidence citations" in template_content.lower():
            quality_reqs["min_citations_per_paragraph"] = 2
        
        # Look for evidence coverage requirements
        if "evidence coverage" in template_content.lower():
            quality_reqs["requires_evidence_coverage"] = True
        
        return quality_reqs
    
    def _infer_industry_sector(self, inputs: InputsI, evidence_bundle: Optional[EvidenceBundle]) -> str:
        """Infer industry sector from inputs and evidence."""
        # Try to extract from evidence first
        if evidence_bundle:
            for item in evidence_bundle.items:
                if "sector" in item.title.lower() or "industry" in item.title.lower():
                    return "Technology"  # Default for now
        
        return "General Industry"
    
    def _create_industry_summary(self, evidence_bundle: Optional[EvidenceBundle]) -> str:
        """Create industry positioning summary."""
        if not evidence_bundle:
            return "Industry positioning analysis pending evidence availability."
        
        return "Well-positioned within industry with competitive advantages and market share stability."
    
    def _create_competitive_summary(self, evidence_bundle: Optional[EvidenceBundle]) -> str:
        """Create competitive advantages summary."""
        if not evidence_bundle:
            return "Competitive analysis pending evidence availability."
        
        return "Sustainable competitive advantages through technology, brand, and operational excellence."
    
    def _create_growth_summary(self, inputs: InputsI, evidence_bundle: Optional[EvidenceBundle]) -> str:
        """Create growth drivers summary."""
        growth_rates = inputs.drivers.sales_growth[:3] if inputs.drivers.sales_growth else [0.05]
        avg_growth = sum(growth_rates) / len(growth_rates)
        return f"Growth outlook: {avg_growth:.1%} average over near term"
    
    def _create_risk_summary(self, evidence_bundle: Optional[EvidenceBundle]) -> str:
        """Create risk factors summary."""
        if not evidence_bundle:
            return "Risk assessment pending evidence availability."
        
        return "Key risks include competitive pressure, execution challenges, and market volatility."
    
    def _create_growth_context(self, context: PromptContext) -> str:
        """Create growth context string."""
        return f"Near-term growth drivers support {context.expected_return or 'moderate'}% expected returns"
    
    def _create_margin_context(self, context: PromptContext) -> str:
        """Create margin context string."""
        return f"Operating margin optimization through efficiency initiatives (tax rate: {context.tax_rate:.1%})"
    
    def _create_wacc_context(self, context: PromptContext) -> str:
        """Create WACC context string."""
        return "Cost of capital reflects current market conditions and company risk profile"
    
    def _get_peer_companies(self, context: PromptContext) -> str:
        """Get peer companies list."""
        return "Industry peer analysis based on comparable companies and market positioning"
    
    def _get_market_position(self, context: PromptContext) -> str:
        """Get market position summary."""
        return f"{context.company_name} maintains competitive market position with strategic advantages"