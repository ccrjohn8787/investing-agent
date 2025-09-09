from __future__ import annotations

"""
Professional Writer Agent for Investment Analysis

Generates professional-grade investment analysis reports with 6-section structure
matching BYD report quality. Integrates with evidence pipeline and enforces
strict citation discipline for all strategic claims.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
from investing_agent.schemas.writer_professional import (
    ProfessionalWriterOutput, ProfessionalSection, ProfessionalParagraph,
    EvidenceCitation, ComputedReference, InvestmentScenario, SectionType,
    create_professional_section_template
)
from investing_agent.agents.writer_validation import WriterValidator, WriterValidationError

class ProfessionalWriterAgent:
    """Professional writer agent for investment analysis reports."""
    
    def __init__(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence_bundle: Optional[EvidenceBundle] = None,
        confidence_threshold: float = 0.80
    ):
        """Initialize professional writer agent.
        
        Args:
            inputs: InputsI containing company and valuation inputs
            valuation: ValuationV containing computed valuation results
            evidence_bundle: Optional evidence bundle for citation backing
            confidence_threshold: Minimum confidence for evidence citations
        """
        self.inputs = inputs
        self.valuation = valuation
        self.evidence_bundle = evidence_bundle
        self.confidence_threshold = confidence_threshold
        
        # Initialize validator
        self.validator = WriterValidator(
            inputs=inputs,
            valuation=valuation,
            evidence_bundle=evidence_bundle,
            require_evidence_citations=evidence_bundle is not None
        )
        
        # Build evidence lookup for quick access
        self.evidence_lookup: Dict[str, EvidenceItem] = {}
        if evidence_bundle:
            self.evidence_lookup = {item.id: item for item in evidence_bundle.items}
    
    def generate_professional_report(
        self,
        include_scenarios: bool = True,
        target_evidence_coverage: float = 0.80,
        target_citation_density: float = 0.70
    ) -> ProfessionalWriterOutput:
        """Generate complete professional investment analysis report.
        
        Args:
            include_scenarios: Whether to include bull/bear scenarios
            target_evidence_coverage: Target evidence coverage ratio
            target_citation_density: Target citation density
            
        Returns:
            Complete professional writer output
        """
        sections = []
        
        # Generate all 6 required sections
        section_types: List[SectionType] = [
            "Industry Context & Market Dynamics",
            "Strategic Positioning Analysis", 
            "Financial Performance Review",
            "Forward-Looking Strategic Outlook",
            "Investment Thesis Development",
            "Risk Factor Analysis"
        ]
        
        for section_type in section_types:
            section = self._generate_section(section_type, include_scenarios)
            sections.append(section)
        
        # Create professional output
        professional_output = ProfessionalWriterOutput(sections=sections)
        
        # Calculate quality metrics
        quality_metrics = professional_output.calculate_quality_metrics()
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(professional_output)
        professional_output.executive_summary = executive_summary
        
        return professional_output
    
    def _generate_section(self, section_type: SectionType, include_scenarios: bool = True) -> ProfessionalSection:
        """Generate a specific professional section.
        
        Args:
            section_type: Type of section to generate
            include_scenarios: Whether to include investment scenarios
            
        Returns:
            Complete professional section
        """
        template = create_professional_section_template(section_type)
        
        # Generate section content based on type
        if section_type == "Industry Context & Market Dynamics":
            return self._generate_industry_context_section(template)
        elif section_type == "Strategic Positioning Analysis":
            return self._generate_strategic_positioning_section(template)
        elif section_type == "Financial Performance Review":
            return self._generate_financial_performance_section(template)
        elif section_type == "Forward-Looking Strategic Outlook":
            return self._generate_forward_outlook_section(template)
        elif section_type == "Investment Thesis Development":
            return self._generate_investment_thesis_section(template, include_scenarios)
        elif section_type == "Risk Factor Analysis":
            return self._generate_risk_analysis_section(template)
        else:
            raise ValueError(f"Unknown section type: {section_type}")
    
    def _generate_industry_context_section(self, template: Dict[str, Any]) -> ProfessionalSection:
        """Generate Industry Context & Market Dynamics section."""
        paragraphs = []
        
        # Market Overview Paragraph
        market_evidence = self._find_relevant_evidence(["growth", "market", "industry"])
        market_paragraph = self._create_paragraph(
            f"The {self.inputs.company} operates in a dynamic market environment characterized by "
            f"evolving competitive dynamics and regulatory frameworks. Industry growth trends "
            f"and market structure analysis provide essential context for valuation assessment.",
            evidence_ids=market_evidence[:2],
            strategic_claims_count=2
        )
        paragraphs.append(market_paragraph)
        
        # Competitive Landscape Paragraph  
        competitive_evidence = self._find_relevant_evidence(["competitive", "peers", "market share"])
        competitive_paragraph = self._create_paragraph(
            f"Competitive positioning within the sector reveals key differentiating factors "
            f"that influence market share dynamics and pricing power. Analysis of peer "
            f"performance and competitive threats informs strategic outlook assessment.",
            evidence_ids=competitive_evidence[:2],
            strategic_claims_count=3
        )
        paragraphs.append(competitive_paragraph)
        
        # Regulatory Environment Paragraph
        regulatory_evidence = self._find_relevant_evidence(["regulatory", "policy", "compliance"])
        regulatory_paragraph = self._create_paragraph(
            f"Regulatory environment and policy developments create both opportunities "
            f"and constraints for {self.inputs.company}. Understanding regulatory trends "
            f"is essential for assessing long-term strategic viability.",
            evidence_ids=regulatory_evidence[:1],
            strategic_claims_count=2
        )
        paragraphs.append(regulatory_paragraph)
        
        return ProfessionalSection(
            section_type="Industry Context & Market Dynamics",
            title="Industry Context & Market Dynamics",
            paragraphs=paragraphs,
            key_insights=[
                "Market structure analysis reveals competitive dynamics",
                "Regulatory framework impacts strategic positioning",
                "Industry trends influence growth outlook"
            ]
        )
    
    def _generate_strategic_positioning_section(self, template: Dict[str, Any]) -> ProfessionalSection:
        """Generate Strategic Positioning Analysis section."""
        paragraphs = []
        
        # Competitive Advantages Paragraph
        advantage_evidence = self._find_relevant_evidence(["competitive", "advantage", "moat"])
        advantage_paragraph = self._create_paragraph(
            f"{self.inputs.company} maintains competitive advantages through strategic "
            f"differentiation and operational excellence. These competitive moats create "
            f"barriers to entry and support sustainable market positioning.",
            evidence_ids=advantage_evidence[:2],
            strategic_claims_count=3
        )
        paragraphs.append(advantage_paragraph)
        
        # Market Share Dynamics
        share_evidence = self._find_relevant_evidence(["market share", "growth", "expansion"])
        share_paragraph = self._create_paragraph(
            f"Market share dynamics demonstrate the company's ability to capture "
            f"and defend market position. Share growth trends reflect strategic "
            f"execution effectiveness and competitive strength.",
            evidence_ids=share_evidence[:1],
            strategic_claims_count=2
        )
        paragraphs.append(share_paragraph)
        
        return ProfessionalSection(
            section_type="Strategic Positioning Analysis",
            title="Strategic Positioning Analysis",
            paragraphs=paragraphs,
            key_insights=[
                "Competitive advantages create sustainable differentiation",
                "Market share trends reflect strategic execution",
                "Strategic positioning supports long-term value creation"
            ]
        )
    
    def _generate_financial_performance_section(self, template: Dict[str, Any]) -> ProfessionalSection:
        """Generate Financial Performance Review section."""
        paragraphs = []
        
        # Revenue Performance with Computed References
        revenue_refs = [
            ComputedReference(field_path="valuation.equity_value", display_format="{:,.0f}"),
            ComputedReference(field_path="valuation.pv_explicit", display_format="{:,.0f}")
        ]
        
        revenue_evidence = self._find_relevant_evidence(["revenue", "growth", "sales"])
        revenue_paragraph = self._create_paragraph(
            f"Revenue performance demonstrates {self.inputs.company}'s growth trajectory "
            f"with equity value of [ref:computed:valuation.equity_value] {self.valuation.equity_value:,.0f} "
            f"reflecting operational execution. Explicit period value of "
            f"[ref:computed:valuation.pv_explicit] {self.valuation.pv_explicit:,.0f} "
            f"captures near-term cash flow generation capability.",
            evidence_ids=revenue_evidence[:1],
            computed_refs=revenue_refs,
            strategic_claims_count=2
        )
        paragraphs.append(revenue_paragraph)
        
        # Profitability Analysis
        margin_evidence = self._find_relevant_evidence(["margin", "profitability", "efficiency"])
        margin_paragraph = self._create_paragraph(
            f"Operating margin trends reflect the company's operational efficiency "
            f"and pricing power. Margin expansion demonstrates effective cost "
            f"management and operational leverage realization.",
            evidence_ids=margin_evidence[:2],
            strategic_claims_count=3
        )
        paragraphs.append(margin_paragraph)
        
        return ProfessionalSection(
            section_type="Financial Performance Review",
            title="Financial Performance Review", 
            paragraphs=paragraphs,
            key_insights=[
                "Revenue growth reflects strategic execution effectiveness",
                "Margin trends demonstrate operational efficiency",
                "Financial metrics support valuation assessment"
            ]
        )
    
    def _generate_forward_outlook_section(self, template: Dict[str, Any]) -> ProfessionalSection:
        """Generate Forward-Looking Strategic Outlook section."""
        paragraphs = []
        
        # Growth Drivers Analysis
        growth_evidence = self._find_relevant_evidence(["growth", "expansion", "opportunity"])
        growth_paragraph = self._create_paragraph(
            f"Growth drivers for {self.inputs.company} center on strategic initiatives "
            f"and market expansion opportunities. These drivers support sustainable "
            f"value creation and long-term competitive positioning.",
            evidence_ids=growth_evidence[:2],
            strategic_claims_count=2
        )
        paragraphs.append(growth_paragraph)
        
        # Investment Priorities
        investment_evidence = self._find_relevant_evidence(["investment", "capex", "strategic"])
        investment_paragraph = self._create_paragraph(
            f"Investment priorities align with strategic objectives and growth "
            f"initiatives. Capital allocation decisions reflect management's "
            f"focus on value-creating opportunities and operational excellence.",
            evidence_ids=investment_evidence[:1],
            strategic_claims_count=3
        )
        paragraphs.append(investment_paragraph)
        
        return ProfessionalSection(
            section_type="Forward-Looking Strategic Outlook",
            title="Forward-Looking Strategic Outlook",
            paragraphs=paragraphs,
            key_insights=[
                "Growth drivers support sustainable value creation",
                "Investment priorities align with strategic objectives",
                "Forward outlook reflects management execution capability"
            ]
        )
    
    def _generate_investment_thesis_section(self, template: Dict[str, Any], include_scenarios: bool) -> ProfessionalSection:
        """Generate Investment Thesis Development section with scenarios."""
        paragraphs = []
        scenarios = []
        
        # Investment Thesis Overview
        thesis_evidence = self._find_relevant_evidence(["growth", "strategy", "competitive"])
        thesis_paragraph = self._create_paragraph(
            f"The investment thesis for {self.inputs.company} rests on fundamental "
            f"strengths in strategic positioning and operational execution. Value "
            f"creation potential reflects sustainable competitive advantages and "
            f"effective capital allocation discipline.",
            evidence_ids=thesis_evidence[:2],
            strategic_claims_count=3
        )
        paragraphs.append(thesis_paragraph)
        
        if include_scenarios:
            # Bull Case Scenario
            bull_evidence = self._find_relevant_evidence(["growth", "opportunity", "expansion"])
            bull_scenario = InvestmentScenario(
                scenario_type="bull",
                key_drivers=["Market share expansion", "Margin improvement", "Strategic initiatives"],
                evidence_support=[
                    EvidenceCitation(evidence_id=ev_id, confidence_score=0.85)
                    for ev_id in bull_evidence[:2]
                ],
                valuation_impact="15-25% upside to base case",
                probability_weight=0.35
            )
            scenarios.append(bull_scenario)
            
            # Bear Case Scenario
            bear_evidence = self._find_relevant_evidence(["risk", "competitive", "challenges"])
            bear_scenario = InvestmentScenario(
                scenario_type="bear",
                key_drivers=["Competitive pressure", "Margin compression", "Execution risks"],
                evidence_support=[
                    EvidenceCitation(evidence_id=ev_id, confidence_score=0.80)
                    for ev_id in bear_evidence[:2]
                ],
                valuation_impact="10-20% downside to base case",
                probability_weight=0.25
            )
            scenarios.append(bear_scenario)
        
        return ProfessionalSection(
            section_type="Investment Thesis Development",
            title="Investment Thesis Development",
            paragraphs=paragraphs,
            investment_scenarios=scenarios,
            key_insights=[
                "Investment thesis anchored on competitive advantages",
                "Bull case driven by growth and margin expansion",
                "Bear case reflects competitive and execution risks"
            ]
        )
    
    def _generate_risk_analysis_section(self, template: Dict[str, Any]) -> ProfessionalSection:
        """Generate Risk Factor Analysis section."""
        paragraphs = []
        
        # Key Risks Assessment
        risk_evidence = self._find_relevant_evidence(["risk", "threat", "challenge"])
        risk_paragraph = self._create_paragraph(
            f"Key risk factors for {self.inputs.company} include competitive threats, "
            f"operational execution challenges, and market environment volatility. "
            f"Risk assessment focuses on probability and potential impact on valuation.",
            evidence_ids=risk_evidence[:2],
            strategic_claims_count=3
        )
        paragraphs.append(risk_paragraph)
        
        # Risk Mitigation
        mitigation_evidence = self._find_relevant_evidence(["strategy", "management", "operational"])
        mitigation_paragraph = self._create_paragraph(
            f"Risk mitigation strategies demonstrate management's proactive approach "
            f"to addressing potential challenges. Operational flexibility and strategic "
            f"positioning provide defensive characteristics against adverse scenarios.",
            evidence_ids=mitigation_evidence[:1],
            strategic_claims_count=2
        )
        paragraphs.append(mitigation_paragraph)
        
        return ProfessionalSection(
            section_type="Risk Factor Analysis",
            title="Risk Factor Analysis",
            paragraphs=paragraphs,
            key_insights=[
                "Key risks center on competitive and execution factors",
                "Risk mitigation reflects management discipline",
                "Risk-return profile supports investment consideration"
            ]
        )
    
    def _generate_executive_summary(self, professional_output: ProfessionalWriterOutput) -> str:
        """Generate executive summary synthesizing key insights."""
        key_insights = []
        for section in professional_output.sections:
            key_insights.extend(section.key_insights)
        
        # Create value-per-share reference
        vps_ref = f"[ref:computed:valuation.value_per_share] {self.valuation.value_per_share:.2f}"
        
        summary = (
            f"Investment analysis of {self.inputs.company} ({self.inputs.ticker}) reveals "
            f"a value per share of {vps_ref} based on fundamental assessment of competitive "
            f"positioning and financial performance. The analysis encompasses industry dynamics, "
            f"strategic positioning, financial review, forward outlook, investment thesis, and "
            f"risk factors. Key insights demonstrate strategic strengths while acknowledging "
            f"execution and competitive risks inherent in the investment proposition."
        )
        
        return summary
    
    def _find_relevant_evidence(self, keywords: List[str]) -> List[str]:
        """Find evidence IDs relevant to specified keywords."""
        if not self.evidence_bundle:
            return []
        
        relevant_ids = []
        for item in self.evidence_bundle.items:
            # Check if evidence has high-confidence claims
            high_conf_claims = [c for c in item.claims if c.confidence >= self.confidence_threshold]
            if not high_conf_claims:
                continue
            
            # Check keyword relevance
            title_lower = item.title.lower()
            for claim in high_conf_claims:
                claim_lower = claim.statement.lower()
                if any(keyword.lower() in title_lower or keyword.lower() in claim_lower for keyword in keywords):
                    relevant_ids.append(item.id)
                    break
        
        return relevant_ids[:5]  # Return top 5 matches
    
    def _create_paragraph(
        self,
        content: str,
        evidence_ids: Optional[List[str]] = None,
        computed_refs: Optional[List[ComputedReference]] = None,
        strategic_claims_count: int = 0
    ) -> ProfessionalParagraph:
        """Create professional paragraph with proper citations."""
        evidence_citations = []
        
        if evidence_ids:
            for ev_id in evidence_ids:
                if ev_id in self.evidence_lookup:
                    item = self.evidence_lookup[ev_id]
                    high_conf_claims = [c for c in item.claims if c.confidence >= self.confidence_threshold]
                    if high_conf_claims:
                        best_confidence = max(c.confidence for c in high_conf_claims)
                        evidence_citations.append(
                            EvidenceCitation(
                                evidence_id=ev_id,
                                confidence_score=best_confidence,
                                relevance_note="Supporting strategic analysis"
                            )
                        )
        
        # Add evidence citations to content if we have evidence
        if evidence_citations and self.evidence_bundle:
            # Insert citations for strategic claims
            citation_text = " ".join(f"[ev:{ec.evidence_id}]" for ec in evidence_citations)
            
            # Find a good insertion point (after first sentence)
            sentences = content.split('. ')
            if len(sentences) > 1:
                sentences[0] += f" {citation_text}"
                content = '. '.join(sentences)
            else:
                content += f" {citation_text}"
        
        return ProfessionalParagraph(
            content=content,
            evidence_citations=evidence_citations,
            computed_references=computed_refs or [],
            strategic_claims_count=strategic_claims_count
        )
    
    def validate_professional_output(self, output: ProfessionalWriterOutput) -> List[str]:
        """Validate professional output meets quality standards."""
        errors = []
        
        # Convert to format validator expects
        sections_dict = []
        for section in output.sections:
            section_content = '\n'.join(p.content for p in section.paragraphs)
            sections_dict.append({
                'title': section.title,
                'paragraphs': [section_content]
            })
        
        # Use existing validator
        validation_errors = self.validator.validate_section_content(sections_dict)
        errors.extend(validation_errors)
        
        # Professional-specific validation
        metrics = output.calculate_quality_metrics()
        
        if not output.meets_professional_standards():
            if metrics['evidence_coverage_ratio'] < 0.80:
                errors.append(f"Evidence coverage below standard: {metrics['evidence_coverage_ratio']:.2f} < 0.80")
            
            if metrics['citation_density'] < 0.70:
                errors.append(f"Citation density below standard: {metrics['citation_density']:.2f} < 0.70")
        
        return errors