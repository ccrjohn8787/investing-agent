from __future__ import annotations

"""
Professional Writer Schema for Investment Analysis Reports

Defines the structure for professional 6-section narrative reports matching
BYD report quality with strict citation discipline and evidence backing.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator

SectionType = Literal[
    "Industry Context & Market Dynamics",
    "Strategic Positioning Analysis", 
    "Financial Performance Review",
    "Forward-Looking Strategic Outlook",
    "Investment Thesis Development",
    "Risk Factor Analysis"
]

class EvidenceCitation(BaseModel):
    """Evidence citation with validation requirements."""
    evidence_id: str = Field(..., description="Evidence item ID (e.g., 'ev_abc123')")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Evidence confidence score")
    relevance_note: Optional[str] = Field(None, description="Why this evidence supports the claim")
    
    @field_validator('evidence_id')
    @classmethod
    def validate_evidence_id_format(cls, v):
        if not v.startswith('ev_'):
            raise ValueError('Evidence ID must start with "ev_"')
        return v

class ComputedReference(BaseModel):
    """Reference to computed valuation values."""
    field_path: str = Field(..., description="Path to computed field (e.g., 'valuation.value_per_share')")
    display_format: Optional[str] = Field(None, description="Display format (e.g., '${:.2f}', '{:,.0f}')")
    
class InvestmentScenario(BaseModel):
    """Investment scenario (bull/bear case) with evidence backing."""
    scenario_type: Literal["bull", "bear", "base"] = Field(..., description="Type of investment scenario")
    key_drivers: List[str] = Field(..., description="Key value drivers for this scenario")
    evidence_support: List[EvidenceCitation] = Field(..., description="Evidence citations supporting scenario")
    valuation_impact: Optional[str] = Field(None, description="Expected valuation impact range")
    probability_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Subjective probability weight")

class ProfessionalParagraph(BaseModel):
    """Professional paragraph with citation tracking."""
    content: str = Field(..., description="Paragraph content with embedded citations")
    evidence_citations: List[EvidenceCitation] = Field(default_factory=list, description="Evidence citations used")
    computed_references: List[ComputedReference] = Field(default_factory=list, description="Computed value references")
    strategic_claims_count: int = Field(default=0, description="Number of strategic claims requiring evidence")
    
    @field_validator('content')
    @classmethod
    def validate_content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Paragraph content cannot be empty')
        return v

class ProfessionalSection(BaseModel):
    """Professional section with comprehensive structure."""
    section_type: SectionType = Field(..., description="Type of professional section")
    title: str = Field(..., description="Section title")
    paragraphs: List[ProfessionalParagraph] = Field(..., description="Section paragraphs")
    key_insights: List[str] = Field(default_factory=list, description="Key insights for this section")
    investment_scenarios: List[InvestmentScenario] = Field(default_factory=list, description="Investment scenarios (for thesis section)")
    
    @field_validator('paragraphs')
    @classmethod
    def validate_paragraphs_not_empty(cls, v):
        if not v:
            raise ValueError('Section must have at least one paragraph')
        return v
    
    def get_total_evidence_citations(self) -> int:
        """Get total number of evidence citations in this section."""
        total = 0
        for paragraph in self.paragraphs:
            total += len(paragraph.evidence_citations)
        for scenario in self.investment_scenarios:
            total += len(scenario.evidence_support)
        return total
    
    def get_citation_density(self) -> float:
        """Calculate citation density (citations per strategic claim)."""
        total_strategic_claims = sum(p.strategic_claims_count for p in self.paragraphs)
        total_citations = self.get_total_evidence_citations()
        
        if total_strategic_claims == 0:
            return 1.0 if total_citations == 0 else float('inf')
        
        return total_citations / total_strategic_claims

class ProfessionalWriterOutput(BaseModel):
    """Complete professional writer output with quality metrics."""
    sections: List[ProfessionalSection] = Field(..., description="Professional narrative sections")
    executive_summary: Optional[str] = Field(None, description="Executive summary synthesis")
    quality_metrics: Dict[str, Any] = Field(default_factory=dict, description="Quality assessment metrics")
    evidence_coverage_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Evidence coverage ratio")
    citation_discipline_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Citation discipline ratio")
    
    @field_validator('sections')
    @classmethod 
    def validate_required_sections(cls, v):
        required_sections = {
            "Industry Context & Market Dynamics",
            "Strategic Positioning Analysis", 
            "Financial Performance Review",
            "Forward-Looking Strategic Outlook",
            "Investment Thesis Development",
            "Risk Factor Analysis"
        }
        
        provided_sections = {section.section_type for section in v}
        missing_sections = required_sections - provided_sections
        
        if missing_sections:
            raise ValueError(f'Missing required sections: {missing_sections}')
        
        return v
    
    def calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics."""
        total_evidence_citations = sum(section.get_total_evidence_citations() for section in self.sections)
        total_strategic_claims = sum(
            sum(p.strategic_claims_count for p in section.paragraphs) 
            for section in self.sections
        )
        total_paragraphs = sum(len(section.paragraphs) for section in self.sections)
        
        # Calculate metrics
        evidence_coverage = (
            total_evidence_citations / max(total_strategic_claims, 1)
            if total_strategic_claims > 0 else 0.0
        )
        
        citation_density = total_evidence_citations / max(total_paragraphs, 1)
        
        # Section-specific metrics
        section_metrics = {}
        for section in self.sections:
            section_metrics[section.section_type] = {
                'paragraphs': len(section.paragraphs),
                'evidence_citations': section.get_total_evidence_citations(),
                'citation_density': section.get_citation_density(),
                'key_insights': len(section.key_insights)
            }
        
        # Investment scenarios analysis (for thesis section)
        thesis_section = next((s for s in self.sections if s.section_type == "Investment Thesis Development"), None)
        scenario_analysis = {}
        if thesis_section:
            scenarios = thesis_section.investment_scenarios
            scenario_analysis = {
                'total_scenarios': len(scenarios),
                'bull_scenarios': len([s for s in scenarios if s.scenario_type == "bull"]),
                'bear_scenarios': len([s for s in scenarios if s.scenario_type == "bear"]),
                'evidence_per_scenario': (
                    sum(len(s.evidence_support) for s in scenarios) / max(len(scenarios), 1)
                )
            }
        
        quality_metrics = {
            'total_sections': len(self.sections),
            'total_paragraphs': total_paragraphs,
            'total_evidence_citations': total_evidence_citations,
            'total_strategic_claims': total_strategic_claims,
            'evidence_coverage_ratio': min(evidence_coverage, 1.0),
            'citation_density': citation_density,
            'section_metrics': section_metrics,
            'scenario_analysis': scenario_analysis,
            'professional_structure_complete': len(self.sections) == 6
        }
        
        # Update instance attributes
        evidence_coverage_ratio = quality_metrics['evidence_coverage_ratio']
        self.evidence_coverage_score = evidence_coverage_ratio if isinstance(evidence_coverage_ratio, float) else 0.0
        self.citation_discipline_score = min(citation_density / 0.7, 1.0)  # Target ≥0.7 citations per paragraph
        self.quality_metrics = quality_metrics
        
        return quality_metrics
    
    def meets_professional_standards(self, min_evidence_coverage: float = 0.80, min_citation_density: float = 0.70) -> bool:
        """Check if output meets professional standards."""
        metrics = self.calculate_quality_metrics()
        
        return (
            metrics['evidence_coverage_ratio'] >= min_evidence_coverage and
            metrics['citation_density'] >= min_citation_density and
            metrics['professional_structure_complete'] and
            len(self.sections) == 6
        )

def create_professional_section_template(section_type: SectionType) -> Dict[str, Any]:
    """Create template structure for each professional section type."""
    templates = {
        "Industry Context & Market Dynamics": {
            "focus_areas": ["sector growth trends", "regulatory environment", "competitive landscape"],
            "required_evidence": ["market research", "industry reports", "regulatory filings"],
            "key_metrics": ["market size", "growth rates", "competitive positioning"]
        },
        "Strategic Positioning Analysis": {
            "focus_areas": ["competitive advantages", "market share dynamics", "differentiation factors"],
            "required_evidence": ["competitive analysis", "market share data", "company strategy documents"],
            "key_metrics": ["market share", "competitive moats", "strategic initiatives"]
        },
        "Financial Performance Review": {
            "focus_areas": ["historical performance", "operational efficiency", "financial trends"],
            "required_evidence": ["financial statements", "management commentary", "operational metrics"],
            "key_metrics": ["revenue growth", "margin trends", "capital efficiency"]
        },
        "Forward-Looking Strategic Outlook": {
            "focus_areas": ["growth drivers", "expansion plans", "investment priorities"],
            "required_evidence": ["management guidance", "strategic plans", "investment announcements"],
            "key_metrics": ["projected growth", "capex plans", "strategic investments"]
        },
        "Investment Thesis Development": {
            "focus_areas": ["bull case drivers", "bear case risks", "scenario analysis"],
            "required_evidence": ["comprehensive evidence synthesis", "scenario modeling", "valuation sensitivity"],
            "key_metrics": ["scenario probabilities", "valuation ranges", "risk-return profiles"]
        },
        "Risk Factor Analysis": {
            "focus_areas": ["key risks", "impact assessment", "mitigation strategies"],
            "required_evidence": ["risk disclosures", "management commentary", "industry analysis"],
            "key_metrics": ["risk severity", "probability assessment", "impact quantification"]
        }
    }
    
    return templates.get(section_type, {})