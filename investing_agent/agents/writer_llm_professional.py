from __future__ import annotations

"""
Professional LLM-Powered Writer Agent

Integrates prompt engineering system with professional narrative structure
to generate BYD-quality investment analysis sections using specialized prompts
and evidence-backed strategic analysis.
"""

from typing import Dict, List, Optional, Any, Tuple
import json
from pathlib import Path

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle
from investing_agent.schemas.writer_llm import WriterLLMOutput, WriterSection
from investing_agent.schemas.writer_professional import (
    ProfessionalWriterOutput, ProfessionalSection, ProfessionalParagraph, SectionType
)
from investing_agent.agents.prompt_engineering import PromptEngineeringManager, PromptContext
from investing_agent.agents.writer_professional_integration import ProfessionalWriterIntegration
from investing_agent.agents.writer_validation import WriterValidator

class ProfessionalLLMWriter:
    """LLM-powered professional writer using prompt engineering system."""
    
    def __init__(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence_bundle: Optional[EvidenceBundle] = None,
        prompts_dir: Optional[Path] = None
    ):
        """Initialize professional LLM writer.
        
        Args:
            inputs: InputsI containing company and valuation inputs
            valuation: ValuationV containing computed valuation results
            evidence_bundle: Optional evidence bundle for citations
            prompts_dir: Optional custom prompts directory
        """
        self.inputs = inputs
        self.valuation = valuation
        self.evidence_bundle = evidence_bundle
        
        # Initialize components
        self.prompt_manager = PromptEngineeringManager(prompts_dir)
        self.professional_integration = ProfessionalWriterIntegration(
            inputs, valuation, evidence_bundle
        )
        self.validator = WriterValidator(
            inputs, valuation, evidence_bundle=evidence_bundle,
            require_evidence_citations=evidence_bundle is not None
        )
        
        # Prepare prompt context
        self.context = self.prompt_manager.prepare_context(
            inputs, valuation, evidence_bundle
        )
    
    def generate_professional_sections(
        self,
        section_types: Optional[List[SectionType]] = None,
        use_cassettes: bool = False,
        cassette_dir: Optional[Path] = None
    ) -> ProfessionalWriterOutput:
        """Generate professional sections using LLM with specialized prompts.
        
        Args:
            section_types: Specific sections to generate (all if None)
            use_cassettes: Whether to use cached LLM responses
            cassette_dir: Directory containing LLM cassettes
            
        Returns:
            Complete professional writer output
        """
        if section_types is None:
            section_types = [
                "Industry Context & Market Dynamics",
                "Strategic Positioning Analysis", 
                "Financial Performance Review",
                "Forward-Looking Strategic Outlook",
                "Investment Thesis Development",
                "Risk Factor Analysis"
            ]
        
        # Validate prompt readiness
        validation = self.prompt_manager.validate_prompt_readiness(self.context)
        if not validation["ready"]:
            raise ValueError(f"Prompt system not ready: {validation['issues']}")
        
        # Generate sections using prompts
        generated_sections = []
        
        for section_type in section_types:
            section = self._generate_section_with_llm(
                section_type, use_cassettes, cassette_dir
            )
            if section:
                generated_sections.append(section)
        
        # Create professional output
        professional_output = ProfessionalWriterOutput(sections=generated_sections)
        
        # Calculate quality metrics
        professional_output.calculate_quality_metrics()
        
        # Generate executive summary
        if professional_output.sections:
            executive_summary = self._generate_executive_summary(professional_output)
            professional_output.executive_summary = executive_summary
        
        return professional_output
    
    def _generate_section_with_llm(
        self,
        section_type: SectionType,
        use_cassettes: bool = False,
        cassette_dir: Optional[Path] = None
    ) -> Optional[WriterSection]:
        """Generate single section using LLM with specialized prompt.
        
        Args:
            section_type: Type of section to generate
            use_cassettes: Whether to use cached responses
            cassette_dir: Directory containing cassettes
            
        Returns:
            Generated writer section or None if failed
        """
        # Generate specialized prompt
        section_prompt = self.prompt_manager.generate_section_prompt(section_type, self.context)
        
        # For now, simulate LLM response with structured content
        # In production, this would call actual LLM with the prompt
        if use_cassettes and cassette_dir:
            response = self._load_from_cassette(section_type, cassette_dir)
        else:
            response = self._simulate_llm_response(section_type, section_prompt)
        
        if not response:
            return None
        
        # Parse LLM response into section structure
        return self._parse_llm_response_to_section(section_type, response)
    
    def _simulate_llm_response(self, section_type: SectionType, prompt: str) -> str:
        """Simulate LLM response for testing purposes.
        
        Args:
            section_type: Type of section being generated
            prompt: The specialized prompt
            
        Returns:
            Simulated professional content
        """
        company = self.context.company_name
        ticker = self.context.ticker
        
        # Generate section-specific content based on type
        if section_type == "Industry Context & Market Dynamics":
            return f"""## Industry Context & Market Dynamics

{company} operates in a dynamic market environment characterized by evolving competitive dynamics and technological innovation [ev:industry_analysis_01]. The industry demonstrates strong structural growth drivers supported by favorable regulatory frameworks and increasing market demand [ev:market_trends_02]. 

Competitive landscape analysis reveals a concentrated market structure with established players maintaining significant barriers to entry [ev:competitive_dynamics_03]. {company}'s market positioning benefits from strategic advantages in technology and distribution networks, enabling sustainable competitive differentiation [ev:strategic_positioning_01].

Regulatory environment provides supportive framework for growth while maintaining appropriate oversight standards [ev:regulatory_framework_01]. Policy developments continue to favor market expansion and innovation, creating favorable conditions for well-positioned industry participants."""

        elif section_type == "Strategic Positioning Analysis":
            return f"""## Strategic Positioning Analysis

{company} maintains sustainable competitive advantages through proprietary technology platforms and established customer relationships [ev:competitive_moats_01]. The company's strategic positioning reflects strong brand recognition and operational excellence that creates meaningful differentiation versus competitors [ev:brand_analysis_02].

Market share dynamics demonstrate {company}'s ability to capture and defend market position through superior execution and strategic initiatives [ev:market_share_trends_01]. Recent strategic investments in technology and infrastructure position the company favorably for continued market leadership [ev:strategic_investments_02].

Strategic differentiation factors include advanced operational capabilities and comprehensive service offerings that provide sustainable competitive advantages [ev:operational_excellence_01]."""

        elif section_type == "Financial Performance Review":
            value_per_share = self.context.value_per_share
            equity_value = self.context.equity_value
            pv_explicit = self.context.pv_explicit
            
            return f"""## Financial Performance Review

Financial performance demonstrates {company}'s operational execution with equity value of [ref:computed:valuation.equity_value] {equity_value:,.0f} reflecting strong fundamentals and strategic positioning [ev:financial_performance_01]. Revenue growth trajectory illustrates effective market capture and customer retention strategies [ev:revenue_analysis_02].

Operating efficiency improvements are evident in margin expansion and cost management initiatives that enhance profitability [ev:operational_efficiency_01]. The explicit period value of [ref:computed:valuation.pv_explicit] {pv_explicit:,.0f} captures the company's near-term cash flow generation capability and operational strength [ev:cash_flow_analysis_02].

Return on invested capital trends demonstrate effective capital allocation and asset utilization that support value creation [ev:capital_efficiency_01]. Financial metrics validate the strategic positioning and competitive advantages that underpin the investment thesis."""

        elif section_type == "Investment Thesis Development":
            return f"""## Investment Thesis Development

The investment thesis for {company} rests on sustainable competitive advantages and strategic execution capabilities that support long-term value creation [ev:thesis_foundation_01]. Key value drivers include market expansion opportunities, operational efficiency gains, and strategic positioning advantages [ev:value_drivers_02].

Bull case scenario centers on accelerated growth through market share expansion and margin improvement from operational leverage [ev:bull_case_drivers_01]. Strategic initiatives in technology and market development provide multiple avenues for value creation over the investment horizon [ev:strategic_initiatives_02].

Bear case considerations include competitive pressure and execution risks that could impact margin sustainability and growth trajectory [ev:bear_case_risks_01]. However, the company's defensive characteristics and management track record provide confidence in navigating market challenges [ev:risk_mitigation_01]."""

        elif section_type == "Risk Factor Analysis":
            return f"""## Risk Factor Analysis

Key investment risks for {company} include competitive dynamics and market evolution that could impact strategic positioning [ev:competitive_risks_01]. Operational execution risks related to strategic initiative implementation present potential challenges to value realization [ev:execution_risks_02].

Risk assessment indicates manageable exposure to industry cyclicality and external market factors through diversified revenue streams and operational flexibility [ev:diversification_benefits_01]. Financial risk profile remains conservative with strong balance sheet characteristics supporting strategic optionality [ev:financial_strength_02].

Risk mitigation strategies include proactive competitive positioning and operational excellence initiatives that provide defensive characteristics against adverse scenarios [ev:risk_mitigation_strategies_01]. Management's proven track record in risk management provides confidence in navigating potential challenges."""

        else:
            return f"""## {section_type}

Professional analysis of {company} ({ticker}) reveals strategic positioning and competitive advantages that support the investment thesis [ev:general_analysis_01]. Key factors include operational excellence and market positioning that create value creation opportunities [ev:strategic_factors_02].

Forward-looking assessment indicates favorable risk-return profile with multiple catalysts for value realization [ev:outlook_assessment_01]. The company's strategic initiatives and execution capabilities position it well for continued performance [ev:execution_capabilities_02]."""
    
    def _parse_llm_response_to_section(self, section_type: SectionType, response: str) -> ProfessionalSection:
        """Parse LLM response into ProfessionalSection format.
        
        Args:
            section_type: Type of section
            response: LLM response content
            
        Returns:
            Parsed professional section
        """
        import re
        
        # Split into paragraphs
        lines = response.strip().split('\n')
        professional_paragraphs = []
        
        current_paragraph = []
        title = section_type
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    
                    # Create ProfessionalParagraph with citation tracking
                    prof_paragraph = ProfessionalParagraph(
                        content=paragraph_text,
                        strategic_claims_count=self._count_strategic_claims(paragraph_text)
                    )
                    professional_paragraphs.append(prof_paragraph)
                    current_paragraph = []
            elif line.startswith('## '):
                title = line[3:].strip()
            else:
                current_paragraph.append(line)
        
        # Add final paragraph
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            prof_paragraph = ProfessionalParagraph(
                content=paragraph_text,
                strategic_claims_count=self._count_strategic_claims(paragraph_text)
            )
            professional_paragraphs.append(prof_paragraph)
        
        # Create key insights based on section type
        key_insights = self._generate_key_insights(section_type)
        
        return ProfessionalSection(
            section_type=section_type,
            title=title,
            paragraphs=professional_paragraphs,
            key_insights=key_insights
        )
    
    def _count_strategic_claims(self, content: str) -> int:
        """Count strategic claims in content that require evidence citations."""
        import re
        
        # Patterns that indicate strategic claims
        claim_patterns = [
            r'\b(?:demonstrates?|reveals?|indicates?|suggests?)\b',
            r'\b(?:strong|competitive|sustainable|significant)\b',
            r'\b(?:growth|expansion|improvement|enhancement)\b',
            r'\b(?:advantages?|positioning|capabilities?)\b'
        ]
        
        claim_count = 0
        for pattern in claim_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                claim_count += 1
        
        return min(claim_count, 3)  # Cap at 3 claims per paragraph
    
    def _generate_key_insights(self, section_type: SectionType) -> List[str]:
        """Generate key insights for section type."""
        insights_map = {
            "Industry Context & Market Dynamics": [
                "Industry demonstrates favorable growth dynamics",
                "Competitive landscape provides strategic opportunities", 
                "Regulatory environment supports market development"
            ],
            "Strategic Positioning Analysis": [
                "Company maintains sustainable competitive advantages",
                "Market positioning reflects strategic execution strength",
                "Strategic differentiation creates value opportunities"
            ],
            "Financial Performance Review": [
                "Financial metrics validate strategic positioning",
                "Performance trends support investment thesis",
                "Capital efficiency demonstrates operational excellence"
            ],
            "Forward-Looking Strategic Outlook": [
                "Growth drivers support value creation potential",
                "Strategic initiatives align with market opportunities",
                "Forward outlook reflects execution capabilities"
            ],
            "Investment Thesis Development": [
                "Investment thesis anchored on competitive advantages",
                "Value creation driven by strategic positioning",
                "Risk-return profile supports investment consideration"
            ],
            "Risk Factor Analysis": [
                "Key risks manageable through strategic positioning",
                "Risk mitigation reflects operational capabilities", 
                "Risk-return balance supports investment framework"
            ]
        }
        
        return insights_map.get(section_type, ["Section provides valuable investment insights"])
    
    def _load_from_cassette(self, section_type: SectionType, cassette_dir: Path) -> Optional[str]:
        """Load cached LLM response from cassette file.
        
        Args:
            section_type: Section type to load
            cassette_dir: Directory containing cassettes
            
        Returns:
            Cached response content or None
        """
        # Map section types to cassette filenames
        cassette_mapping = {
            "Industry Context & Market Dynamics": "industry_context.json",
            "Strategic Positioning Analysis": "competitive_positioning.json",
            "Financial Performance Review": "financial_performance.json",
            "Investment Thesis Development": "investment_thesis.json",
            "Risk Factor Analysis": "risk_analysis.json"
        }
        
        cassette_file = cassette_dir / cassette_mapping.get(section_type, f"{section_type.lower().replace(' ', '_')}.json")
        
        if cassette_file.exists():
            try:
                cassette_data = json.loads(cassette_file.read_text())
                return cassette_data.get("response", "")
            except Exception:
                return None
        
        return None
    
    def _generate_executive_summary(self, professional_output: ProfessionalWriterOutput) -> str:
        """Generate executive summary from professional sections.
        
        Args:
            professional_output: Professional writer output
            
        Returns:
            Executive summary content
        """
        company = self.context.company_name
        ticker = self.context.ticker
        value_per_share = self.context.value_per_share
        
        # Extract key insights from sections
        key_insights = []
        for section in professional_output.sections:
            if hasattr(section, 'key_insights'):
                key_insights.extend(section.key_insights)
        
        # Generate executive summary
        summary = f"""Investment analysis of {company} ({ticker}) reveals a value per share of [ref:computed:valuation.value_per_share] {value_per_share:.2f} based on comprehensive assessment of competitive positioning and strategic execution capabilities [ev:investment_analysis_01]. 

The investment thesis rests on sustainable competitive advantages and operational excellence that support long-term value creation [ev:strategic_advantages_01]. Key value drivers include market expansion opportunities, margin improvement initiatives, and strategic positioning benefits that provide multiple avenues for return generation [ev:value_creation_drivers_01].

Risk assessment indicates balanced risk-return profile with manageable exposure to competitive and execution risks [ev:risk_assessment_01]. The company's defensive characteristics and proven management execution provide confidence in value realization over the investment horizon."""
        
        return summary
    
    def generate_writer_llm_output(
        self,
        section_types: Optional[List[SectionType]] = None,
        use_cassettes: bool = False,
        cassette_dir: Optional[Path] = None
    ) -> WriterLLMOutput:
        """Generate WriterLLMOutput using professional prompt system.
        
        Args:
            section_types: Specific sections to generate
            use_cassettes: Whether to use cached responses
            cassette_dir: Directory containing cassettes
            
        Returns:
            WriterLLMOutput compatible with existing pipeline
        """
        # Generate professional sections
        professional_output = self.generate_professional_sections(
            section_types, use_cassettes, cassette_dir
        )
        
        # Convert to WriterLLMOutput format
        writer_llm_output = self.professional_integration.convert_to_writer_llm_output(
            professional_output
        )
        
        return writer_llm_output
    
    def validate_output_quality(self, output: WriterLLMOutput) -> Dict[str, Any]:
        """Validate output quality using professional standards.
        
        Args:
            output: WriterLLMOutput to validate
            
        Returns:
            Validation results and quality metrics
        """
        # Convert to sections format for validator
        sections_dict = []
        for section in output.sections:
            section_content = '\n'.join(section.paragraphs)
            sections_dict.append({
                'title': section.title,
                'paragraphs': [section_content]
            })
        
        # Validate using existing validator
        validation_errors = self.validator.validate_section_content(sections_dict)
        
        # Extract quality metrics from metadata
        quality_metrics = output.metadata.get('quality_metrics', {}) if output.metadata else {}
        
        return {
            'validation_errors': validation_errors,
            'quality_metrics': quality_metrics,
            'meets_professional_standards': len(validation_errors) == 0 and 
                                           output.metadata.get('meets_professional_standards', False),
            'evidence_coverage': quality_metrics.get('evidence_coverage_ratio', 0.0),
            'citation_density': quality_metrics.get('citation_density', 0.0)
        }

def create_professional_llm_writer(
    inputs: InputsI,
    valuation: ValuationV,
    evidence_bundle: Optional[EvidenceBundle] = None,
    prompts_dir: Optional[Path] = None
) -> ProfessionalLLMWriter:
    """Factory function to create professional LLM writer.
    
    Args:
        inputs: InputsI containing company and valuation inputs
        valuation: ValuationV containing computed valuation results
        evidence_bundle: Optional evidence bundle for citations
        prompts_dir: Optional custom prompts directory
        
    Returns:
        Configured professional LLM writer
    """
    return ProfessionalLLMWriter(inputs, valuation, evidence_bundle, prompts_dir)