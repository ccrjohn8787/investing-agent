"""Professional LLM Writer for generating investment narratives."""

from __future__ import annotations

from typing import Dict, Any, Optional
import logging

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class WriterLLMGen:
    """Generate professional investment narratives using LLM."""
    
    def __init__(self):
        """Initialize the writer with LLM provider."""
        self.provider = LLMProvider()
        
    def generate_professional_narrative(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence: Optional[Any] = None,
        sensitivity: Optional[Any] = None
    ) -> Dict[str, str]:
        """Generate professional narrative sections.
        
        Args:
            inputs: Valuation inputs
            valuation: Valuation results
            evidence: Evidence bundle (optional)
            sensitivity: Sensitivity analysis (optional)
            
        Returns:
            Dictionary of narrative sections
        """
        sections = {}
        
        # Executive Summary
        try:
            sections['executive_summary'] = self._generate_executive_summary(
                inputs, valuation, evidence
            )
        except Exception as e:
            logger.warning(f"Failed to generate executive summary: {e}")
            sections['executive_summary'] = self._fallback_executive_summary(inputs, valuation)
        
        # Financial Analysis
        try:
            sections['financial_analysis'] = self._generate_financial_analysis(
                inputs, valuation
            )
        except Exception as e:
            logger.warning(f"Failed to generate financial analysis: {e}")
            sections['financial_analysis'] = ""
        
        # Investment Thesis
        try:
            sections['investment_thesis'] = self._generate_investment_thesis(
                inputs, valuation, evidence
            )
        except Exception as e:
            logger.warning(f"Failed to generate investment thesis: {e}")
            sections['investment_thesis'] = ""
        
        # Risk Analysis
        try:
            sections['risk_analysis'] = self._generate_risk_analysis(
                inputs, valuation
            )
        except Exception as e:
            logger.warning(f"Failed to generate risk analysis: {e}")
            sections['risk_analysis'] = ""
        
        # Industry Context
        try:
            sections['industry_context'] = self._generate_industry_context(
                inputs, evidence
            )
        except Exception as e:
            logger.warning(f"Failed to generate industry context: {e}")
            sections['industry_context'] = ""
        
        # Conclusion
        try:
            sections['conclusion'] = self._generate_conclusion(
                inputs, valuation
            )
        except Exception as e:
            logger.warning(f"Failed to generate conclusion: {e}")
            sections['conclusion'] = self._fallback_conclusion(inputs, valuation)
        
        return sections
    
    def _generate_executive_summary(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence: Optional[Any] = None
    ) -> str:
        """Generate executive summary section."""
        
        # Calculate key metrics
        revenue_growth = inputs.drivers.sales_growth[0] * 100
        margin = inputs.drivers.oper_margin[0] * 100
        upside = ((valuation.value_per_share / 350.0) - 1) * 100  # Assuming $350 current price
        
        # Calculate enterprise value from components
        ev = valuation.pv_oper_assets + valuation.net_debt - valuation.cash_nonop
        
        prompt = f"""Generate a professional executive summary for {inputs.company} ({inputs.ticker}).

Key Valuation Results:
- Fair Value per Share: ${valuation.value_per_share:.2f}
- Enterprise Value: ${ev / 1e9:.1f}B
- Revenue Growth (Y1): {revenue_growth:.1f}%
- Operating Margin: {margin:.1f}%
- Upside Potential: {upside:.1f}%

Requirements:
1. Start with a compelling investment thesis statement
2. Include 3-5 key investment highlights as bullet points
3. Mention the fair value and upside potential
4. Be concise but comprehensive (200-300 words)
5. Use professional investment language
6. Focus on value drivers and competitive advantages

Generate only the executive summary text, no headers or formatting codes."""
        
        try:
            response = self.provider.call(
                "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional equity research analyst writing investment reports."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": 0.3, "max_tokens": 500}
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed for executive summary: {e}")
            return self._fallback_executive_summary(inputs, valuation)
    
    def _generate_financial_analysis(
        self,
        inputs: InputsI,
        valuation: ValuationV
    ) -> str:
        """Generate financial analysis section."""
        
        revenue_growth_path = [g * 100 for g in inputs.drivers.sales_growth[:5]]
        margin_path = [m * 100 for m in inputs.drivers.oper_margin[:5]]
        
        prompt = f"""Generate a professional financial analysis for {inputs.company}.

Financial Metrics:
- Revenue (T0): ${inputs.revenue_t0 / 1e9:.1f}B
- Revenue Growth Path (5Y): {revenue_growth_path}
- Operating Margin Path (5Y): {margin_path}
- Tax Rate: {inputs.tax_rate * 100:.1f}%
- WACC: {inputs.wacc[0] * 100:.1f}%

Requirements:
1. Analyze revenue growth drivers and sustainability
2. Discuss margin expansion/contraction factors
3. Assess capital efficiency and ROIC
4. Include specific numbers and trends
5. Be analytical and data-driven (200-250 words)

Generate only the analysis text, no headers."""
        
        try:
            response = self.provider.call(
                "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial analyst providing detailed investment analysis."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": 0.2, "max_tokens": 400}
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed for financial analysis: {e}")
            return ""
    
    def _generate_investment_thesis(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence: Optional[Any] = None
    ) -> str:
        """Generate investment thesis section."""
        
        prompt = f"""Generate a compelling investment thesis for {inputs.company} ({inputs.ticker}).

Valuation:
- Fair Value: ${valuation.value_per_share:.2f}
- Current assumptions: Growth {inputs.drivers.sales_growth[0]*100:.1f}%, Margin {inputs.drivers.oper_margin[0]*100:.1f}%

Requirements:
1. Present 3 key pillars supporting the investment case
2. Each pillar should have specific supporting points
3. Include both quantitative and qualitative factors
4. Address competitive moat and market position
5. Be persuasive but balanced (250-300 words)

Format as structured thesis with clear sections."""
        
        try:
            response = self.provider.call(
                "gpt-4",
                messages=[
                    {"role": "system", "content": "You are an investment strategist building compelling investment cases."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": 0.3, "max_tokens": 500}
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed for investment thesis: {e}")
            return ""
    
    def _generate_risk_analysis(
        self,
        inputs: InputsI,
        valuation: ValuationV
    ) -> str:
        """Generate risk analysis section."""
        
        prompt = f"""Generate a comprehensive risk analysis for {inputs.company}.

Company Context:
- Ticker: {inputs.ticker}
- Fair Value: ${valuation.value_per_share:.2f}
- Key Assumptions: Growth {inputs.drivers.sales_growth[0]*100:.1f}%, Margin {inputs.drivers.oper_margin[0]*100:.1f}%

Requirements:
1. Identify 3-4 major risk categories
2. Include specific risk factors under each category
3. Discuss potential impact on valuation
4. Mention any mitigating factors
5. Be thorough but concise (200-250 words)

Structure with clear risk categories and bullets."""
        
        try:
            response = self.provider.call(
                "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a risk analyst evaluating investment risks."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": 0.2, "max_tokens": 400}
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed for risk analysis: {e}")
            return ""
    
    def _generate_industry_context(
        self,
        inputs: InputsI,
        evidence: Optional[Any] = None
    ) -> str:
        """Generate industry context section."""
        
        prompt = f"""Generate industry context and competitive positioning analysis for {inputs.company} ({inputs.ticker}).

Requirements:
1. Describe the industry landscape and key trends
2. Analyze competitive positioning and market share
3. Discuss barriers to entry and competitive advantages
4. Include industry growth prospects
5. Be specific to the company's sector (200-250 words)

Focus on strategic positioning and competitive dynamics."""
        
        try:
            response = self.provider.call(
                "gpt-4",
                messages=[
                    {"role": "system", "content": "You are an industry analyst providing strategic market analysis."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": 0.3, "max_tokens": 400}
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed for industry context: {e}")
            return ""
    
    def _generate_conclusion(
        self,
        inputs: InputsI,
        valuation: ValuationV
    ) -> str:
        """Generate conclusion section."""
        
        # Calculate enterprise value
        ev = valuation.pv_oper_assets + valuation.net_debt - valuation.cash_nonop
        
        prompt = f"""Generate a strong conclusion for the investment report on {inputs.company}.

Key Points:
- Fair Value: ${valuation.value_per_share:.2f}
- Enterprise Value: ${ev / 1e9:.1f}B
- Growth assumption: {inputs.drivers.sales_growth[0]*100:.1f}%
- Margin assumption: {inputs.drivers.oper_margin[0]*100:.1f}%

Requirements:
1. Synthesize the investment case
2. Restate fair value and recommendation
3. Mention key opportunities and risks
4. End with clear investment rating
5. Be decisive and actionable (150-200 words)

Include a clear BUY/HOLD/SELL rating with price target."""
        
        try:
            response = self.provider.call(
                "gpt-4", 
                messages=[
                    {"role": "system", "content": "You are a senior analyst providing final investment recommendations."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": 0.2, "max_tokens": 300}
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM call failed for conclusion: {e}")
            return self._fallback_conclusion(inputs, valuation)
    
    def _fallback_executive_summary(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Fallback executive summary when LLM fails."""
        return f"""
{inputs.company} ({inputs.ticker}) presents an investment opportunity with a DCF-derived fair value of ${valuation.value_per_share:.2f} per share. 
Our analysis is based on revenue growth of {inputs.drivers.sales_growth[0]*100:.1f}% in Year 1, moderating to a terminal growth rate of {inputs.drivers.stable_growth*100:.1f}%, 
and operating margins evolving from {inputs.drivers.oper_margin[0]*100:.1f}% to {inputs.drivers.stable_margin*100:.1f}% at maturity.

Key Investment Highlights:
• **Valuation Upside**: Fair value of ${valuation.value_per_share:.2f} suggests meaningful appreciation potential
• **Growth Trajectory**: Revenue growth path supports sustained value creation
• **Margin Profile**: Operating leverage expected to drive profitability expansion
• **Capital Efficiency**: Disciplined capital allocation enhancing shareholder returns
"""
    
    def _fallback_conclusion(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Fallback conclusion when LLM fails."""
        return f"""
Based on our comprehensive DCF analysis, we derive a fair value of ${valuation.value_per_share:.2f} per share for {inputs.company}. 
The valuation reflects our assumptions of {inputs.drivers.sales_growth[0]*100:.1f}% near-term revenue growth and {inputs.drivers.oper_margin[0]*100:.1f}% operating margins, 
with a weighted average cost of capital of {inputs.wacc[0]*100:.1f}%.

While risks exist around execution and market dynamics, the company's competitive position and growth prospects support our constructive view. 
We rate {inputs.ticker} as a BUY with a 12-month price target of ${valuation.value_per_share * 0.9:.2f} (10% discount to fair value for margin of safety).
"""