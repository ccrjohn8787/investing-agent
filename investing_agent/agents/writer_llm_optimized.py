"""Optimized LLM Writer using cheaper models strategically."""

from __future__ import annotations

from typing import Dict, Any, Optional
import logging
import os

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class OptimizedLLMWriter:
    """Generate professional investment narratives using cost-optimized model selection."""
    
    # Model selection strategy for different sections
    # DEFAULT: GPT-4o-mini for cost efficiency
    # Only use GPT-4 when explicitly requested via premium mode
    MODEL_STRATEGY = {
        "executive_summary": {
            "premium": "gpt-4",           # $0.03/1K in (USE ONLY WHEN EXPLICITLY REQUESTED)
            "standard": "gpt-4o-mini",    # $0.00015/1K in (DEFAULT - 200x cheaper!)
            "budget": "gpt-3.5-turbo"     # $0.0005/1K in (60x cheaper)
        },
        "financial_analysis": {
            "premium": "gpt-4",
            "standard": "gpt-4o-mini",    # Good at numbers
            "budget": "gpt-3.5-turbo"
        },
        "investment_thesis": {
            "premium": "gpt-4",
            "standard": "gpt-4o-mini",    # Creative enough
            "budget": "gpt-3.5-turbo"
        },
        "risk_analysis": {
            "premium": "gpt-4o-mini",     # Don't need GPT-4 for risks
            "standard": "gpt-3.5-turbo",
            "budget": "gpt-3.5-turbo"
        },
        "industry_context": {
            "premium": "gpt-4o-mini",     # Good enough for context
            "standard": "gpt-3.5-turbo",
            "budget": "gpt-3.5-turbo"
        },
        "conclusion": {
            "premium": "gpt-4",           # Important section
            "standard": "gpt-4o-mini",
            "budget": "gpt-3.5-turbo"
        }
    }
    
    def __init__(self, quality_mode: str = "standard"):
        """Initialize with quality mode.
        
        Args:
            quality_mode: "premium" (GPT-4), "standard" (GPT-4o-mini), or "budget" (GPT-3.5)
        """
        self.provider = LLMProvider()
        self.quality_mode = quality_mode
        self.cost_tracker = {"total_cost": 0.0, "sections": {}}
        
    def generate_professional_narrative(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        evidence: Optional[Any] = None,
        sensitivity: Optional[Any] = None
    ) -> Dict[str, str]:
        """Generate professional narrative sections with optimized model selection."""
        
        sections = {}
        
        # Executive Summary - Use better model if in premium mode
        model = self._get_model_for_section("executive_summary")
        sections['executive_summary'] = self._generate_section(
            "executive_summary", 
            model,
            self._get_executive_summary_prompt(inputs, valuation),
            fallback=self._fallback_executive_summary(inputs, valuation)
        )
        
        # Financial Analysis - GPT-4o-mini is great with numbers
        model = self._get_model_for_section("financial_analysis")
        sections['financial_analysis'] = self._generate_section(
            "financial_analysis",
            model,
            self._get_financial_analysis_prompt(inputs, valuation)
        )
        
        # Investment Thesis - Important section
        model = self._get_model_for_section("investment_thesis")
        sections['investment_thesis'] = self._generate_section(
            "investment_thesis",
            model,
            self._get_investment_thesis_prompt(inputs, valuation)
        )
        
        # Risk Analysis - Can use cheaper model
        model = self._get_model_for_section("risk_analysis")
        sections['risk_analysis'] = self._generate_section(
            "risk_analysis",
            model,
            self._get_risk_analysis_prompt(inputs, valuation)
        )
        
        # Industry Context - Can use cheaper model
        model = self._get_model_for_section("industry_context")
        sections['industry_context'] = self._generate_section(
            "industry_context",
            model,
            self._get_industry_context_prompt(inputs)
        )
        
        # Conclusion - Important, but can optimize
        model = self._get_model_for_section("conclusion")
        sections['conclusion'] = self._generate_section(
            "conclusion",
            model,
            self._get_conclusion_prompt(inputs, valuation),
            fallback=self._fallback_conclusion(inputs, valuation)
        )
        
        # Log cost summary
        self._log_cost_summary()
        
        return sections
    
    def _get_model_for_section(self, section: str) -> str:
        """Get the appropriate model for a section based on quality mode."""
        return self.MODEL_STRATEGY[section][self.quality_mode]
    
    def _generate_section(
        self, 
        section_name: str,
        model: str,
        prompt: str,
        fallback: str = "",
        max_tokens: int = 400
    ) -> str:
        """Generate a section with cost tracking."""
        
        try:
            # Adjust temperature based on model
            temperature = 0.3 if "gpt-4" in model else 0.5
            
            response = self.provider.call(
                model,
                messages=[
                    {"role": "system", "content": "You are a professional equity research analyst."},
                    {"role": "user", "content": prompt}
                ],
                params={"temperature": temperature, "max_tokens": max_tokens}
            )
            
            # Track cost (rough estimates)
            self._track_cost(section_name, model, len(prompt), len(response))
            
            return response.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate {section_name}: {e}")
            return fallback
    
    def _track_cost(self, section: str, model: str, input_chars: int, output_chars: int):
        """Track cost for each section."""
        
        # Rough token estimation (1 token ≈ 4 chars)
        input_tokens = input_chars / 4
        output_tokens = output_chars / 4
        
        # Cost per 1K tokens (approximate)
        costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
        
        model_costs = costs.get(model, costs["gpt-3.5-turbo"])
        cost = (input_tokens * model_costs["input"] + 
                output_tokens * model_costs["output"]) / 1000
        
        self.cost_tracker["sections"][section] = {
            "model": model,
            "cost": cost
        }
        self.cost_tracker["total_cost"] += cost
    
    def _log_cost_summary(self):
        """Log the cost summary."""
        if os.getenv("LLM_COST_TRACKING") == "true":
            logger.info(f"Report Generation Cost Summary:")
            logger.info(f"  Total Cost: ${self.cost_tracker['total_cost']:.4f}")
            for section, details in self.cost_tracker["sections"].items():
                logger.info(f"  - {section}: ${details['cost']:.4f} ({details['model']})")
    
    # Prompt methods (simplified versions)
    def _get_executive_summary_prompt(self, inputs: InputsI, valuation: ValuationV) -> str:
        ev = valuation.pv_oper_assets + valuation.net_debt - valuation.cash_nonop
        return f"""Generate executive summary for {inputs.company} ({inputs.ticker}).
Fair Value: ${valuation.value_per_share:.2f}
Revenue Growth: {inputs.drivers.sales_growth[0]*100:.1f}%
Margin: {inputs.drivers.oper_margin[0]*100:.1f}%

Create compelling 200-word summary with investment thesis and 3-5 bullet points."""
    
    def _get_financial_analysis_prompt(self, inputs: InputsI, valuation: ValuationV) -> str:
        return f"""Analyze financials for {inputs.company}:
Revenue: ${inputs.revenue_t0/1e9:.1f}B
Growth: {inputs.drivers.sales_growth[0]*100:.1f}%
Margin: {inputs.drivers.oper_margin[0]*100:.1f}%
WACC: {inputs.wacc[0]*100:.1f}%

Provide 200-word analysis of growth drivers and profitability."""
    
    def _get_investment_thesis_prompt(self, inputs: InputsI, valuation: ValuationV) -> str:
        return f"""Create investment thesis for {inputs.company} ({inputs.ticker}).
Fair Value: ${valuation.value_per_share:.2f}

Present 3 key pillars supporting the investment case (250 words)."""
    
    def _get_risk_analysis_prompt(self, inputs: InputsI, valuation: ValuationV) -> str:
        return f"""Identify key risks for {inputs.company}:
- Regulatory risks
- Competitive threats  
- Operational challenges

200 words with mitigation factors."""
    
    def _get_industry_context_prompt(self, inputs: InputsI) -> str:
        return f"""Describe industry context for {inputs.company} ({inputs.ticker}).
Focus on competitive position and market dynamics (200 words)."""
    
    def _get_conclusion_prompt(self, inputs: InputsI, valuation: ValuationV) -> str:
        return f"""Conclude investment report for {inputs.company}.
Fair Value: ${valuation.value_per_share:.2f}
Growth: {inputs.drivers.sales_growth[0]*100:.1f}%

Provide clear BUY/HOLD/SELL recommendation (150 words)."""
    
    def _fallback_executive_summary(self, inputs: InputsI, valuation: ValuationV) -> str:
        return f"""{inputs.company} ({inputs.ticker}) shows fair value of ${valuation.value_per_share:.2f}."""
    
    def _fallback_conclusion(self, inputs: InputsI, valuation: ValuationV) -> str:
        return f"""Based on DCF analysis, fair value is ${valuation.value_per_share:.2f}."""