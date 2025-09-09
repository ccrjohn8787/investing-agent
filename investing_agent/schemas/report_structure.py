"""Report structure definitions for professional investment reports."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from enum import Enum


class SectionType(str, Enum):
    """Types of report sections."""
    EXECUTIVE_SUMMARY = "executive_summary"
    INVESTMENT_THESIS = "investment_thesis"
    HISTORICAL_PERFORMANCE = "historical_performance"
    INDUSTRY_ANALYSIS = "industry_analysis"
    COMPETITIVE_POSITIONING = "competitive_positioning"
    FINANCIAL_ANALYSIS = "financial_analysis"
    VALUATION_ANALYSIS = "valuation_analysis"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    FORWARD_OUTLOOK = "forward_outlook"
    RISK_ASSESSMENT = "risk_assessment"
    STRATEGIC_INITIATIVES = "strategic_initiatives"
    ESG_CONSIDERATIONS = "esg_considerations"
    TECHNICAL_APPENDIX = "technical_appendix"


class CompanyProfile(str, Enum):
    """Company profile types for section customization."""
    HIGH_GROWTH = "high_growth"           # Tech, biotech, emerging markets
    MATURE_STABLE = "mature_stable"       # Utilities, consumer staples
    TURNAROUND = "turnaround"            # Restructuring situations
    CYCLICAL = "cyclical"                # Industrials, materials, energy
    DIVIDEND_ARISTOCRAT = "dividend"      # Income-focused companies
    DISRUPTOR = "disruptor"              # Market challengers
    MARKET_LEADER = "market_leader"      # Dominant position companies


class ReportSection(BaseModel):
    """Individual report section configuration."""
    
    section_type: SectionType = Field(description="Type of section")
    title: str = Field(description="Section title")
    subtitle: Optional[str] = Field(None, description="Section subtitle")
    
    # Content configuration
    include_narrative: bool = Field(default=True, description="Include narrative text")
    include_charts: bool = Field(default=False, description="Include visualizations")
    include_tables: bool = Field(default=False, description="Include data tables")
    
    # Specific content elements
    charts: List[str] = Field(default_factory=list, description="Chart IDs to include")
    tables: List[str] = Field(default_factory=list, description="Table IDs to include")
    
    # Section metadata
    priority: int = Field(default=5, description="Section priority (1=highest)")
    word_count_target: int = Field(default=500, description="Target word count")
    evidence_required: bool = Field(default=True, description="Requires evidence citations")
    
    # Conditional inclusion
    required_data: List[str] = Field(default_factory=list, description="Required data for inclusion")
    company_profiles: List[CompanyProfile] = Field(default_factory=list, description="Suitable company profiles")


class ReportStructure(BaseModel):
    """Complete report structure definition."""
    
    report_title: str = Field(description="Main report title")
    report_subtitle: Optional[str] = Field(None, description="Report subtitle")
    
    # Report metadata
    company: str = Field(description="Company name")
    ticker: str = Field(description="Company ticker")
    report_date: str = Field(description="Report date")
    analyst_name: Optional[str] = Field(default="Investing Agent", description="Analyst name")
    
    # Report configuration
    target_length: int = Field(default=3000, description="Target word count")
    include_toc: bool = Field(default=True, description="Include table of contents")
    include_disclaimer: bool = Field(default=True, description="Include disclaimer")
    
    # Sections
    sections: List[ReportSection] = Field(default_factory=list, description="Report sections in order")
    
    # Visual elements
    include_cover_chart: bool = Field(default=True, description="Include cover chart")
    charts_inline: bool = Field(default=True, description="Embed charts inline vs appendix")
    
    # Style configuration
    professional_formatting: bool = Field(default=True)
    color_scheme: str = Field(default="professional_blue")


class SectionTemplate(BaseModel):
    """Template for generating section content."""
    
    section_type: SectionType
    
    # Opening patterns
    opening_patterns: List[str] = Field(description="Opening paragraph patterns")
    
    # Key points to cover
    key_topics: List[str] = Field(description="Key topics to address")
    
    # Evidence requirements
    min_evidence_citations: int = Field(default=3)
    evidence_types: List[str] = Field(default_factory=list)
    
    # Narrative flow
    narrative_structure: List[str] = Field(description="Paragraph structure")
    transition_phrases: List[str] = Field(default_factory=list)
    
    # Closing patterns
    closing_patterns: List[str] = Field(description="Closing paragraph patterns")


def get_standard_sections() -> Dict[SectionType, ReportSection]:
    """Get standard section definitions."""
    
    return {
        SectionType.EXECUTIVE_SUMMARY: ReportSection(
            section_type=SectionType.EXECUTIVE_SUMMARY,
            title="Executive Summary",
            subtitle="Investment Highlights",
            include_narrative=True,
            include_charts=False,
            include_tables=False,
            priority=1,
            word_count_target=300,
            evidence_required=True
        ),
        
        SectionType.INVESTMENT_THESIS: ReportSection(
            section_type=SectionType.INVESTMENT_THESIS,
            title="Investment Thesis",
            subtitle="Key Value Drivers",
            include_narrative=True,
            include_charts=False,
            include_tables=False,
            priority=2,
            word_count_target=500,
            evidence_required=True
        ),
        
        SectionType.HISTORICAL_PERFORMANCE: ReportSection(
            section_type=SectionType.HISTORICAL_PERFORMANCE,
            title="Historical Performance Review",
            include_narrative=True,
            include_charts=True,
            include_tables=True,
            charts=["financial_trajectory"],
            tables=["historical_financials"],
            priority=3,
            word_count_target=400
        ),
        
        SectionType.INDUSTRY_ANALYSIS: ReportSection(
            section_type=SectionType.INDUSTRY_ANALYSIS,
            title="Industry Analysis",
            subtitle="Market Dynamics and Trends",
            include_narrative=True,
            include_charts=True,
            include_tables=False,
            charts=["market_share", "industry_growth"],
            priority=4,
            word_count_target=600,
            required_data=["industry_data"]
        ),
        
        SectionType.COMPETITIVE_POSITIONING: ReportSection(
            section_type=SectionType.COMPETITIVE_POSITIONING,
            title="Competitive Positioning",
            include_narrative=True,
            include_charts=True,
            include_tables=True,
            charts=["competitive_positioning", "peer_multiples"],
            tables=["peer_comparables"],
            priority=4,
            word_count_target=500,
            required_data=["peer_analysis"]
        ),
        
        SectionType.FINANCIAL_ANALYSIS: ReportSection(
            section_type=SectionType.FINANCIAL_ANALYSIS,
            title="Financial Analysis",
            subtitle="Revenue, Margins, and Cash Flow",
            include_narrative=True,
            include_charts=True,
            include_tables=True,
            charts=["financial_trajectory", "margin_evolution"],
            tables=["financial_projections"],
            priority=3,
            word_count_target=700
        ),
        
        SectionType.VALUATION_ANALYSIS: ReportSection(
            section_type=SectionType.VALUATION_ANALYSIS,
            title="Valuation Analysis",
            include_narrative=True,
            include_charts=True,
            include_tables=True,
            charts=["value_bridge"],
            tables=["wacc_evolution", "valuation_summary"],
            priority=2,
            word_count_target=600
        ),
        
        SectionType.SENSITIVITY_ANALYSIS: ReportSection(
            section_type=SectionType.SENSITIVITY_ANALYSIS,
            title="Sensitivity Analysis",
            include_narrative=True,
            include_charts=True,
            include_tables=True,
            charts=["sensitivity_heatmap"],
            tables=["sensitivity"],
            priority=4,
            word_count_target=400
        ),
        
        SectionType.FORWARD_OUTLOOK: ReportSection(
            section_type=SectionType.FORWARD_OUTLOOK,
            title="Forward-Looking Strategy",
            subtitle="Growth Initiatives and Strategic Priorities",
            include_narrative=True,
            include_charts=False,
            include_tables=False,
            priority=3,
            word_count_target=500,
            evidence_required=True
        ),
        
        SectionType.RISK_ASSESSMENT: ReportSection(
            section_type=SectionType.RISK_ASSESSMENT,
            title="Risk Assessment",
            subtitle="Key Risks and Mitigation Strategies",
            include_narrative=True,
            include_charts=False,
            include_tables=True,
            tables=["risk_matrix"],
            priority=3,
            word_count_target=500,
            evidence_required=True
        ),
    }


def get_company_profile(inputs: Any, evidence: Any = None) -> CompanyProfile:
    """Determine company profile based on inputs and evidence."""
    
    # Simplified logic - would be more sophisticated in practice
    growth_rate = 0.10  # Would extract from inputs
    margin_trend = "improving"  # Would analyze from data
    market_position = "leader"  # Would determine from comparables
    
    if growth_rate > 0.20:
        return CompanyProfile.HIGH_GROWTH
    elif growth_rate < 0.05:
        if margin_trend == "declining":
            return CompanyProfile.TURNAROUND
        else:
            return CompanyProfile.MATURE_STABLE
    elif market_position == "leader":
        return CompanyProfile.MARKET_LEADER
    else:
        return CompanyProfile.DISRUPTOR


def select_sections_for_company(company_profile: CompanyProfile,
                               available_data: Dict[str, bool]) -> List[ReportSection]:
    """Select appropriate sections based on company profile and data availability."""
    
    standard_sections = get_standard_sections()
    selected = []
    
    # Always include core sections
    core_sections = [
        SectionType.EXECUTIVE_SUMMARY,
        SectionType.INVESTMENT_THESIS,
        SectionType.FINANCIAL_ANALYSIS,
        SectionType.VALUATION_ANALYSIS
    ]
    
    for section_type in core_sections:
        selected.append(standard_sections[section_type])
    
    # Add profile-specific sections
    if company_profile == CompanyProfile.HIGH_GROWTH:
        selected.extend([
            standard_sections[SectionType.FORWARD_OUTLOOK],
            standard_sections[SectionType.INDUSTRY_ANALYSIS],
            standard_sections[SectionType.RISK_ASSESSMENT]
        ])
    elif company_profile == CompanyProfile.TURNAROUND:
        selected.extend([
            standard_sections[SectionType.HISTORICAL_PERFORMANCE],
            standard_sections[SectionType.STRATEGIC_INITIATIVES],
            standard_sections[SectionType.RISK_ASSESSMENT]
        ])
    elif company_profile == CompanyProfile.MARKET_LEADER:
        selected.extend([
            standard_sections[SectionType.COMPETITIVE_POSITIONING],
            standard_sections[SectionType.INDUSTRY_ANALYSIS],
            standard_sections[SectionType.FORWARD_OUTLOOK]
        ])
    
    # Add data-dependent sections
    if available_data.get("peer_analysis", False):
        if SectionType.COMPETITIVE_POSITIONING not in [s.section_type for s in selected]:
            selected.append(standard_sections[SectionType.COMPETITIVE_POSITIONING])
    
    if available_data.get("sensitivity_data", False):
        selected.append(standard_sections[SectionType.SENSITIVITY_ANALYSIS])
    
    # Sort by priority
    selected.sort(key=lambda x: x.priority)
    
    return selected