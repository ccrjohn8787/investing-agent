from __future__ import annotations

"""
Professional Writer Integration

Integrates professional 6-section narrative structure with existing writer pipeline.
Converts between ProfessionalWriterOutput and WriterLLMOutput for backward compatibility.
"""

from typing import Dict, List, Optional, Any
import re

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle
from investing_agent.schemas.writer_llm import WriterLLMOutput, WriterSection
from investing_agent.schemas.writer_professional import (
    ProfessionalWriterOutput, ProfessionalSection, ProfessionalParagraph
)
from investing_agent.agents.writer_professional import ProfessionalWriterAgent

class ProfessionalWriterIntegration:
    """Integrates professional writer with existing pipeline."""
    
    def __init__(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence_bundle: Optional[EvidenceBundle] = None
    ):
        """Initialize professional writer integration.
        
        Args:
            inputs: InputsI containing company and valuation inputs
            valuation: ValuationV containing computed valuation results
            evidence_bundle: Optional evidence bundle for citations
        """
        self.inputs = inputs
        self.valuation = valuation
        self.evidence_bundle = evidence_bundle
        
        # Initialize professional writer agent
        self.professional_writer = ProfessionalWriterAgent(
            inputs=inputs,
            valuation=valuation,
            evidence_bundle=evidence_bundle
        )
    
    def generate_professional_narrative(
        self,
        target_evidence_coverage: float = 0.80,
        target_citation_density: float = 0.70,
        include_scenarios: bool = True
    ) -> ProfessionalWriterOutput:
        """Generate professional narrative with quality targets.
        
        Args:
            target_evidence_coverage: Target evidence coverage ratio
            target_citation_density: Target citation density ratio
            include_scenarios: Whether to include bull/bear scenarios
            
        Returns:
            Complete professional writer output
        """
        return self.professional_writer.generate_professional_report(
            include_scenarios=include_scenarios,
            target_evidence_coverage=target_evidence_coverage,
            target_citation_density=target_citation_density
        )
    
    def convert_to_writer_llm_output(self, professional_output: ProfessionalWriterOutput) -> WriterLLMOutput:
        """Convert professional output to WriterLLMOutput for backward compatibility.
        
        Args:
            professional_output: Professional writer output
            
        Returns:
            WriterLLMOutput compatible with existing pipeline
        """
        sections = []
        
        for prof_section in professional_output.sections:
            # Convert professional section to simple section
            paragraphs = []
            refs = []
            
            for prof_paragraph in prof_section.paragraphs:
                # Extract content without embedded citations for paragraphs
                clean_content = self._extract_clean_content(prof_paragraph.content)
                paragraphs.append(clean_content)
                
                # Collect references from citations
                for citation in prof_paragraph.evidence_citations:
                    refs.append(f"ev:{citation.evidence_id}")
                
                for comp_ref in prof_paragraph.computed_references:
                    refs.append(f"computed:{comp_ref.field_path}")
            
            # Add investment scenarios as additional paragraphs for thesis section
            if prof_section.section_type == "Investment Thesis Development" and prof_section.investment_scenarios:
                for scenario in prof_section.investment_scenarios:
                    scenario_text = f"{scenario.scenario_type.title()} Case: {', '.join(scenario.key_drivers)}"
                    if scenario.valuation_impact:
                        scenario_text += f" ({scenario.valuation_impact})"
                    paragraphs.append(scenario_text)
                    
                    # Add scenario evidence references
                    for citation in scenario.evidence_support:
                        refs.append(f"ev:{citation.evidence_id}")
            
            writer_section = WriterSection(
                title=prof_section.title,
                paragraphs=paragraphs,
                refs=list(set(refs))  # Remove duplicates
            )
            
            sections.append(writer_section)
        
        # Include quality metrics in metadata
        metadata = {
            "professional_structure": True,
            "quality_metrics": professional_output.quality_metrics,
            "evidence_coverage_score": professional_output.evidence_coverage_score,
            "citation_discipline_score": professional_output.citation_discipline_score,
            "meets_professional_standards": professional_output.meets_professional_standards()
        }
        
        return WriterLLMOutput(sections=sections, metadata=metadata)
    
    def create_enhanced_markdown_output(self, professional_output: ProfessionalWriterOutput) -> str:
        """Create enhanced markdown with professional formatting.
        
        Args:
            professional_output: Professional writer output
            
        Returns:
            Enhanced markdown with professional formatting
        """
        lines = []
        
        # Executive Summary
        if professional_output.executive_summary:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(professional_output.executive_summary)
            lines.append("")
        
        # Professional Sections
        for section in professional_output.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            
            # Section paragraphs
            for paragraph in section.paragraphs:
                lines.append(paragraph.content)
                lines.append("")
            
            # Investment scenarios (for thesis section)
            if section.investment_scenarios:
                lines.append("### Investment Scenarios")
                lines.append("")
                
                for scenario in section.investment_scenarios:
                    lines.append(f"**{scenario.scenario_type.title()} Case**")
                    lines.append(f"- Key Drivers: {', '.join(scenario.key_drivers)}")
                    
                    if scenario.valuation_impact:
                        lines.append(f"- Valuation Impact: {scenario.valuation_impact}")
                    
                    if scenario.probability_weight:
                        lines.append(f"- Probability Weight: {scenario.probability_weight:.1%}")
                    
                    # Evidence support
                    if scenario.evidence_support:
                        evidence_refs = " ".join(f"[ev:{cite.evidence_id}]" for cite in scenario.evidence_support)
                        lines.append(f"- Evidence Support: {evidence_refs}")
                    
                    lines.append("")
            
            # Key insights
            if section.key_insights:
                lines.append("**Key Insights:**")
                for insight in section.key_insights:
                    lines.append(f"- {insight}")
                lines.append("")
        
        # Quality Metrics Summary
        if professional_output.quality_metrics:
            metrics = professional_output.quality_metrics
            lines.append("## Quality Assessment")
            lines.append("")
            lines.append(f"- Evidence Coverage: {metrics['evidence_coverage_ratio']:.1%}")
            lines.append(f"- Citation Density: {metrics['citation_density']:.2f}")
            lines.append(f"- Total Evidence Citations: {metrics['total_evidence_citations']}")
            lines.append(f"- Professional Structure: {'✓' if metrics['professional_structure_complete'] else '✗'}")
            
            if professional_output.meets_professional_standards():
                lines.append("- **Quality Standards: MEETS PROFESSIONAL REQUIREMENTS** ✓")
            else:
                lines.append("- **Quality Standards: Below Professional Standards** ✗")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _extract_clean_content(self, content: str) -> str:
        """Extract content without embedded citations for compatibility."""
        # Remove evidence citations but keep the text readable
        clean_content = re.sub(r'\s*\[ev:[^\]]+\]', '', content)
        
        # Remove computed references (they'll be handled by existing system)
        clean_content = re.sub(r'\s*\[ref:computed:[^\]]+\]', '', clean_content)
        
        # Clean up extra spaces
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        return clean_content
    
    def validate_professional_integration(self) -> Dict[str, Any]:
        """Validate professional writer integration readiness.
        
        Returns:
            Integration validation results
        """
        validation_results = {
            "integration_ready": True,
            "evidence_available": self.evidence_bundle is not None,
            "evidence_items_count": len(self.evidence_bundle.items) if self.evidence_bundle else 0,
            "professional_writer_ready": True,
            "validation_issues": []
        }
        
        # Check evidence availability and quality
        if self.evidence_bundle:
            high_conf_claims = self.evidence_bundle.get_high_confidence_claims(0.80)
            validation_results.update({
                "high_confidence_claims": len(high_conf_claims),
                "evidence_coverage_by_driver": {
                    "growth": len([c for c in high_conf_claims if c.driver == "growth"]),
                    "margin": len([c for c in high_conf_claims if c.driver == "margin"]),
                    "wacc": len([c for c in high_conf_claims if c.driver == "wacc"]),
                    "s2c": len([c for c in high_conf_claims if c.driver == "s2c"])
                }
            })
            
            # Validate evidence quality
            if len(high_conf_claims) < 5:
                validation_results["validation_issues"].append(
                    f"Low high-confidence evidence count: {len(high_conf_claims)} < 5"
                )
            
            driver_coverage = sum(1 for count in validation_results["evidence_coverage_by_driver"].values() if count > 0)
            if driver_coverage < 2:
                validation_results["validation_issues"].append(
                    f"Limited driver coverage: {driver_coverage}/4 drivers have evidence"
                )
        else:
            validation_results["validation_issues"].append("No evidence bundle provided - citations will be disabled")
        
        # Test professional writer instantiation
        try:
            test_output = self.professional_writer.generate_professional_report(
                include_scenarios=False,
                target_evidence_coverage=0.70,
                target_citation_density=0.60
            )
            validation_results["test_generation_successful"] = True
            validation_results["test_sections_generated"] = len(test_output.sections)
            
        except Exception as e:
            validation_results["integration_ready"] = False
            validation_results["professional_writer_ready"] = False
            validation_results["validation_issues"].append(f"Professional writer test failed: {str(e)}")
        
        return validation_results

def create_professional_narrative(
    inputs: InputsI,
    valuation: ValuationV,
    evidence_bundle: Optional[EvidenceBundle] = None,
    output_format: str = "writer_llm",
    include_scenarios: bool = True
) -> Dict[str, Any]:
    """Convenience function to create professional narrative.
    
    Args:
        inputs: InputsI containing company and valuation inputs
        valuation: ValuationV containing computed valuation results
        evidence_bundle: Optional evidence bundle for citations
        output_format: Output format ("writer_llm", "professional", "markdown")
        include_scenarios: Whether to include investment scenarios
        
    Returns:
        Dictionary containing requested output format and metadata
    """
    integration = ProfessionalWriterIntegration(inputs, valuation, evidence_bundle)
    
    # Generate professional narrative
    professional_output = integration.generate_professional_narrative(
        target_evidence_coverage=0.80,
        target_citation_density=0.70,
        include_scenarios=include_scenarios
    )
    
    # Create requested output format
    results = {
        "professional_output": professional_output,
        "quality_metrics": professional_output.quality_metrics,
        "meets_standards": professional_output.meets_professional_standards()
    }
    
    if output_format == "writer_llm":
        results["writer_llm_output"] = integration.convert_to_writer_llm_output(professional_output)
    
    elif output_format == "markdown":
        results["markdown_output"] = integration.create_enhanced_markdown_output(professional_output)
    
    elif output_format == "professional":
        pass  # Professional output already included
    
    else:
        raise ValueError(f"Unknown output format: {output_format}")
    
    return results