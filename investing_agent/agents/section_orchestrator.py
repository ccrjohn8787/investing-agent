"""Dynamic section orchestration for professional reports."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass

from investing_agent.schemas.report_structure import (
    ReportSection, SectionType, CompanyProfile,
    get_company_profile, select_sections_for_company,
    ReportStructure
)
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle
from investing_agent.schemas.comparables import PeerAnalysis


logger = logging.getLogger(__name__)


@dataclass
class SectionContent:
    """Container for section content."""
    section_type: SectionType
    title: str
    narrative: Optional[str] = None
    charts: Dict[str, bytes] = None
    tables: Dict[str, str] = None
    evidence_citations: List[str] = None
    word_count: int = 0


class SectionOrchestrator:
    """Orchestrate dynamic section generation based on context."""
    
    def __init__(self):
        self.section_generators = self._initialize_generators()
        
    def _initialize_generators(self) -> Dict[SectionType, Any]:
        """Initialize section-specific content generators."""
        # Map section types to their generation functions
        return {
            SectionType.EXECUTIVE_SUMMARY: self._generate_executive_summary,
            SectionType.INVESTMENT_THESIS: self._generate_investment_thesis,
            SectionType.HISTORICAL_PERFORMANCE: self._generate_historical_performance,
            SectionType.INDUSTRY_ANALYSIS: self._generate_industry_analysis,
            SectionType.COMPETITIVE_POSITIONING: self._generate_competitive_positioning,
            SectionType.FINANCIAL_ANALYSIS: self._generate_financial_analysis,
            SectionType.VALUATION_ANALYSIS: self._generate_valuation_analysis,
            SectionType.SENSITIVITY_ANALYSIS: self._generate_sensitivity_analysis,
            SectionType.FORWARD_OUTLOOK: self._generate_forward_outlook,
            SectionType.RISK_ASSESSMENT: self._generate_risk_assessment,
        }
    
    def orchestrate_report(self, 
                          inputs: InputsI,
                          valuation: ValuationV,
                          evidence: Optional[EvidenceBundle] = None,
                          peer_analysis: Optional[PeerAnalysis] = None,
                          charts: Optional[Dict[str, bytes]] = None,
                          tables: Optional[Dict[str, str]] = None) -> ReportStructure:
        """Orchestrate complete report generation with dynamic sections."""
        
        # Determine company profile
        company_profile = get_company_profile(inputs, evidence)
        logger.info(f"Company profile identified: {company_profile.value}")
        
        # Assess available data
        available_data = self._assess_data_availability(
            inputs, valuation, evidence, peer_analysis
        )
        
        # Select appropriate sections
        selected_sections = select_sections_for_company(company_profile, available_data)
        logger.info(f"Selected {len(selected_sections)} sections for report")
        
        # Create report structure
        report_structure = ReportStructure(
            report_title=f"{inputs.company} Investment Analysis",
            report_subtitle=self._generate_subtitle(company_profile, valuation),
            company=inputs.company,
            ticker=inputs.ticker,
            report_date=self._get_report_date(),
            sections=selected_sections
        )
        
        return report_structure
    
    def generate_section_content(self,
                                section: ReportSection,
                                inputs: InputsI,
                                valuation: ValuationV,
                                evidence: Optional[EvidenceBundle] = None,
                                peer_analysis: Optional[PeerAnalysis] = None,
                                charts: Optional[Dict[str, bytes]] = None,
                                tables: Optional[Dict[str, str]] = None) -> SectionContent:
        """Generate content for a specific section."""
        
        generator = self.section_generators.get(section.section_type)
        if not generator:
            logger.warning(f"No generator for section type: {section.section_type}")
            return SectionContent(
                section_type=section.section_type,
                title=section.title
            )
        
        return generator(section, inputs, valuation, evidence, peer_analysis, charts, tables)
    
    def _assess_data_availability(self, 
                                 inputs: InputsI,
                                 valuation: ValuationV,
                                 evidence: Optional[EvidenceBundle],
                                 peer_analysis: Optional[PeerAnalysis]) -> Dict[str, bool]:
        """Assess what data is available for section generation."""
        
        return {
            "historical_data": hasattr(inputs, "fundamentals") and inputs.fundamentals is not None,
            "evidence_data": evidence is not None and len(evidence.items) > 0 if evidence else False,
            "peer_analysis": peer_analysis is not None and len(peer_analysis.peer_companies) > 0 if peer_analysis else False,
            "sensitivity_data": hasattr(valuation, "sensitivity") and valuation.sensitivity is not None,
            "industry_data": evidence and any("industry" in item.source_type for item in evidence.items) if evidence else False,
            "forward_guidance": evidence and any("guidance" in item.title.lower() for item in evidence.items) if evidence else False,
        }
    
    def _generate_subtitle(self, company_profile: CompanyProfile, valuation: ValuationV) -> str:
        """Generate dynamic subtitle based on profile and valuation."""
        
        value_indicator = "Undervalued" if valuation.value_per_share > 100 else "Fairly Valued"  # Simplified
        
        profile_subtitles = {
            CompanyProfile.HIGH_GROWTH: f"High-Growth Opportunity in Expanding Market",
            CompanyProfile.MATURE_STABLE: f"Stable Cash Generator with {value_indicator} Entry Point",
            CompanyProfile.TURNAROUND: f"Transformation Story with Significant Upside Potential",
            CompanyProfile.MARKET_LEADER: f"Dominant Position with Sustainable Competitive Advantages",
            CompanyProfile.DISRUPTOR: f"Innovative Challenger Disrupting Traditional Markets",
            CompanyProfile.CYCLICAL: f"Cyclical Opportunity at Attractive Valuation",
            CompanyProfile.DIVIDEND_ARISTOCRAT: f"Reliable Income Generator with Growth Potential"
        }
        
        return profile_subtitles.get(company_profile, f"{value_indicator} Investment Opportunity")
    
    def _get_report_date(self) -> str:
        """Get formatted report date."""
        from datetime import datetime
        return datetime.now().strftime("%B %d, %Y")
    
    # Section generators
    def _generate_executive_summary(self, section: ReportSection, inputs: InputsI,
                                   valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                   peer_analysis: Optional[PeerAnalysis],
                                   charts: Optional[Dict[str, bytes]],
                                   tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate executive summary content."""
        
        narrative = f"""
## {section.title}

**Investment Recommendation:** BUY | **Target Price:** ${valuation.value_per_share:.2f} | **Current Price:** $[MARKET_PRICE]

{inputs.company} ({inputs.ticker}) presents a compelling investment opportunity with significant upside potential. 
Our DCF analysis values the company at ${valuation.value_per_share:.2f} per share, representing [X]% upside from current levels.

**Key Investment Highlights:**
• Strong financial performance with projected revenue CAGR of [X]%
• Expanding margins driven by operational efficiency improvements
• Leading market position with sustainable competitive advantages
• Robust cash generation supporting growth investments and shareholder returns

The investment thesis is supported by [evidence summary if available].
"""
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            word_count=len(narrative.split())
        )
    
    def _generate_investment_thesis(self, section: ReportSection, inputs: InputsI,
                                   valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                   peer_analysis: Optional[PeerAnalysis],
                                   charts: Optional[Dict[str, bytes]],
                                   tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate investment thesis content."""
        
        narrative = f"""
## {section.title}

Our investment thesis for {inputs.company} centers on three key value drivers:

**1. Market Leadership and Competitive Moats**
{inputs.company} has established a dominant position through [competitive advantages]. This leadership translates to 
pricing power, customer loyalty, and sustainable margins above industry averages.

**2. Growth Trajectory and Market Expansion**
The company is well-positioned to capture growth through [growth drivers]. With a total addressable market of $[TAM], 
{inputs.company} has significant runway for expansion.

**3. Financial Excellence and Value Creation**
Strong financial metrics including [key metrics] demonstrate management's ability to create shareholder value. 
The company's capital allocation strategy balances growth investment with shareholder returns.
"""
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            word_count=len(narrative.split())
        )
    
    def _generate_historical_performance(self, section: ReportSection, inputs: InputsI,
                                        valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                        peer_analysis: Optional[PeerAnalysis],
                                        charts: Optional[Dict[str, bytes]],
                                        tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate historical performance analysis."""
        
        narrative = f"""
## {section.title}

{inputs.company} has demonstrated strong historical performance over the past five years:

**Revenue Growth:** The company has achieved consistent top-line growth, with revenues increasing from $[BASE] to 
$[CURRENT], representing a [X]% CAGR. This growth has been driven by [growth drivers].

**Margin Evolution:** Operating margins have expanded from [X]% to [Y]%, reflecting operational improvements and 
scale efficiencies. EBITDA margins now stand at [Z]%, above the industry median.

**Cash Generation:** Free cash flow has grown substantially, reaching $[FCF] in the latest period. The company's 
cash conversion rate of [X]% demonstrates efficient working capital management.
"""
        
        section_charts = {}
        if charts and "financial_trajectory" in charts:
            section_charts["financial_trajectory"] = charts["financial_trajectory"]
        
        section_tables = {}
        if tables and "historical_financials" in tables:
            section_tables["historical_financials"] = tables["historical_financials"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            charts=section_charts,
            tables=section_tables,
            word_count=len(narrative.split())
        )
    
    def _generate_industry_analysis(self, section: ReportSection, inputs: InputsI,
                                   valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                   peer_analysis: Optional[PeerAnalysis],
                                   charts: Optional[Dict[str, bytes]],
                                   tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate industry analysis content."""
        
        narrative = f"""
## {section.title}

The [INDUSTRY] industry represents a $[SIZE] global market experiencing [GROWTH_PATTERN] driven by [KEY_DRIVERS].

**Market Dynamics:**
The industry is characterized by [concentration level] with [competitive dynamics]. Key trends shaping the industry 
include [trend 1], [trend 2], and [trend 3].

**Growth Outlook:**
Industry growth is expected to accelerate, with projections suggesting [X]% CAGR through [YEAR]. This growth will be 
driven by [growth catalysts].

**Competitive Landscape:**
{inputs.company} competes with [key competitors] for market share. The company's [X]% market share positions it as 
a [market position] with opportunities to gain share through [strategies].
"""
        
        section_charts = {}
        if charts and "market_share" in charts:
            section_charts["market_share"] = charts["market_share"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            charts=section_charts,
            word_count=len(narrative.split())
        )
    
    def _generate_competitive_positioning(self, section: ReportSection, inputs: InputsI,
                                         valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                         peer_analysis: Optional[PeerAnalysis],
                                         charts: Optional[Dict[str, bytes]],
                                         tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate competitive positioning analysis."""
        
        narrative = f"""
## {section.title}

{inputs.company} maintains a strong competitive position within its peer group:

**Competitive Advantages:**
• Scale advantages with [metric] exceeding peer median by [X]%
• Technology leadership through [differentiators]
• Brand strength and customer loyalty evidenced by [metrics]
• Operational efficiency with margins [X]bps above peers

**Relative Valuation:**
Trading at [X]x EV/EBITDA compared to peer median of [Y]x, {inputs.company} appears [valuation assessment]. 
This [discount/premium] reflects [factors].

**Market Share Dynamics:**
The company has gained [X]bps of market share over the past [period], primarily at the expense of [competitors]. 
This momentum is expected to continue driven by [catalysts].
"""
        
        section_charts = {}
        if charts:
            if "competitive_positioning" in charts:
                section_charts["competitive_positioning"] = charts["competitive_positioning"]
            if "peer_multiples" in charts:
                section_charts["peer_multiples"] = charts["peer_multiples"]
        
        section_tables = {}
        if tables and "peer_comparables" in tables:
            section_tables["peer_comparables"] = tables["peer_comparables"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            charts=section_charts,
            tables=section_tables,
            word_count=len(narrative.split())
        )
    
    def _generate_financial_analysis(self, section: ReportSection, inputs: InputsI,
                                    valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                    peer_analysis: Optional[PeerAnalysis],
                                    charts: Optional[Dict[str, bytes]],
                                    tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate financial analysis content."""
        
        narrative = f"""
## {section.title}

### Revenue Analysis
Revenue is projected to grow from ${valuation.revenue_projection[0]:.0f}M to ${valuation.revenue_projection[-1]:.0f}M 
over our forecast period, representing a [X]% CAGR. Key drivers include:
• Volume growth of [X]% annually
• Pricing improvements of [Y]% per year
• Mix shift toward higher-margin products

### Margin Evolution
Operating margins are expected to expand from [current]% to [target]% by [year], driven by:
• Operating leverage on fixed cost base
• Efficiency initiatives yielding $[amount]M in savings
• Favorable product mix evolution

### Cash Flow Generation
Free cash flow is projected to reach $[amount]M by [year], with conversion rates improving to [X]%. 
This strong cash generation supports both growth investments and shareholder returns.

### Capital Efficiency
Return on invested capital is expected to reach [X]% by [year], well above the [Y]% cost of capital, 
creating significant economic value.
"""
        
        section_charts = {}
        if charts:
            if "financial_trajectory" in charts:
                section_charts["financial_trajectory"] = charts["financial_trajectory"]
            if "margin_evolution" in charts:
                section_charts["margin_evolution"] = charts["margin_evolution"]
        
        section_tables = {}
        if tables and "financial_projections" in tables:
            section_tables["financial_projections"] = tables["financial_projections"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            charts=section_charts,
            tables=section_tables,
            word_count=len(narrative.split())
        )
    
    def _generate_valuation_analysis(self, section: ReportSection, inputs: InputsI,
                                    valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                    peer_analysis: Optional[PeerAnalysis],
                                    charts: Optional[Dict[str, bytes]],
                                    tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate valuation analysis content."""
        
        narrative = f"""
## {section.title}

### DCF Valuation
Our discounted cash flow analysis yields a fair value of ${valuation.value_per_share:.2f} per share:

• **Operating Cash Flows:** Present value of $[amount]M over [period]
• **Terminal Value:** $[amount]M based on [growth]% perpetual growth
• **Enterprise Value:** $[amount]M after discounting at [WACC]% WACC
• **Equity Value:** $[amount]M after adjusting for net debt of $[amount]M

### Cost of Capital
We apply a weighted average cost of capital of [X]%, derived from:
• Cost of equity: [Y]% (risk-free rate + equity risk premium × beta)
• After-tax cost of debt: [Z]%
• Target capital structure: [debt]% debt, [equity]% equity

### Relative Valuation
On a relative basis, {inputs.company} trades at attractive multiples:
• EV/EBITDA: [X]x vs peer median of [Y]x
• P/E: [X]x vs peer median of [Y]x
• EV/Sales: [X]x vs peer median of [Y]x

### Valuation Summary
Multiple valuation approaches support our ${valuation.value_per_share:.2f} target price, 
representing [X]% upside from current levels.
"""
        
        section_charts = {}
        if charts and "value_bridge" in charts:
            section_charts["value_bridge"] = charts["value_bridge"]
        
        section_tables = {}
        if tables:
            if "wacc_evolution" in tables:
                section_tables["wacc_evolution"] = tables["wacc_evolution"]
            if "valuation_summary" in tables:
                section_tables["valuation_summary"] = tables["valuation_summary"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            charts=section_charts,
            tables=section_tables,
            word_count=len(narrative.split())
        )
    
    def _generate_sensitivity_analysis(self, section: ReportSection, inputs: InputsI,
                                      valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                      peer_analysis: Optional[PeerAnalysis],
                                      charts: Optional[Dict[str, bytes]],
                                      tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate sensitivity analysis content."""
        
        narrative = f"""
## {section.title}

Our valuation shows resilience across a range of scenarios:

### Key Assumptions Sensitivity
The table below shows valuation sensitivity to changes in growth and margin assumptions:

[Sensitivity table will be inserted here]

### Scenario Analysis
• **Base Case (60% probability):** ${valuation.value_per_share:.2f} per share
• **Upside Case (25% probability):** $[upside] per share (+[X]%)
• **Downside Case (15% probability):** $[downside] per share (-[Y]%)

### Key Sensitivities
• A 100bps change in revenue growth impacts valuation by ~[X]%
• A 100bps change in operating margin impacts valuation by ~[Y]%
• A 100bps change in WACC impacts valuation by ~[Z]%

The analysis demonstrates that even under conservative assumptions, significant upside remains.
"""
        
        section_charts = {}
        if charts and "sensitivity_heatmap" in charts:
            section_charts["sensitivity_heatmap"] = charts["sensitivity_heatmap"]
        
        section_tables = {}
        if tables and "sensitivity" in tables:
            section_tables["sensitivity"] = tables["sensitivity"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            charts=section_charts,
            tables=section_tables,
            word_count=len(narrative.split())
        )
    
    def _generate_forward_outlook(self, section: ReportSection, inputs: InputsI,
                                 valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                 peer_analysis: Optional[PeerAnalysis],
                                 charts: Optional[Dict[str, bytes]],
                                 tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate forward-looking strategy content."""
        
        narrative = f"""
## {section.title}

### Strategic Initiatives
{inputs.company}'s forward strategy focuses on several key initiatives:

**1. Market Expansion**
The company is targeting [new markets] with potential to add $[revenue]M in annual revenue by [year]. 
Initial investments of $[amount]M are expected to yield [ROI]% returns.

**2. Product Innovation**
R&D investments of $[amount]M annually are driving next-generation products. The innovation pipeline 
includes [products] with combined revenue potential of $[amount]M.

**3. Operational Excellence**
Cost optimization programs are targeting $[savings]M in annual savings by [year]. Key initiatives include 
automation, supply chain optimization, and administrative efficiency.

### Growth Catalysts
Near-term catalysts that could drive outperformance include:
• [Catalyst 1] expected in [timeframe]
• [Catalyst 2] with potential [impact]
• [Catalyst 3] driving [outcome]

### Long-Term Vision
Management's vision positions {inputs.company} as the [position] by [year], with targets of:
• Revenue: $[amount]M ([X]% CAGR)
• EBITDA margins: [X]% (up [Y]bps)
• Market share: [X]% (up [Y]bps)
"""
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            word_count=len(narrative.split())
        )
    
    def _generate_risk_assessment(self, section: ReportSection, inputs: InputsI,
                                 valuation: ValuationV, evidence: Optional[EvidenceBundle],
                                 peer_analysis: Optional[PeerAnalysis],
                                 charts: Optional[Dict[str, bytes]],
                                 tables: Optional[Dict[str, str]]) -> SectionContent:
        """Generate risk assessment content."""
        
        narrative = f"""
## {section.title}

### Key Risk Factors

**Operational Risks**
• Execution risk on strategic initiatives
• Supply chain disruptions and input cost inflation
• Technology obsolescence and innovation requirements
• Talent retention in competitive labor market

**Market Risks**
• Economic recession impacting demand
• Competitive pressure on pricing and market share
• Regulatory changes affecting operating environment
• Currency fluctuations on international operations

**Financial Risks**
• Leverage constraints with debt/EBITDA at [X]x
• Refinancing risk with $[amount]M due in [year]
• Working capital requirements during growth phase
• Capital allocation balancing growth and returns

### Risk Mitigation
Management has implemented several risk mitigation strategies:
• Diversification across [segments/geographies]
• Hedging programs for [commodity/currency] exposure
• Strong balance sheet with $[cash]M liquidity
• Proven crisis management and business continuity planning

### Risk-Adjusted Returns
Despite these risks, the risk-reward profile remains attractive with:
• Probability-weighted return of [X]%
• Downside protection from [factors]
• Multiple paths to value creation
"""
        
        section_tables = {}
        if tables and "risk_matrix" in tables:
            section_tables["risk_matrix"] = tables["risk_matrix"]
        
        return SectionContent(
            section_type=section.section_type,
            title=section.title,
            narrative=narrative,
            tables=section_tables,
            word_count=len(narrative.split())
        )