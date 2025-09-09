from __future__ import annotations

"""
Professional Investment Report Quality Judge

Evaluates investment reports across 5 dimensions to distinguish between high-quality 
story-to-numbers analysis (like BYD benchmark) and low-quality numbers-only reports 
(like META baseline). Uses deterministic LLM evaluation with comprehensive scoring rubric.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from investing_agent.schemas.report_evaluation import (
    ReportQualityResult, QualityDimension, EvaluationRubric
)


class ReportQualityJudge:
    """Professional investment analyst LLM judge for report quality assessment."""
    
    def __init__(self):
        """Initialize judge with evaluation rubric and scoring criteria."""
        self.dimension_weights = {
            "strategic_narrative": 0.25,
            "analytical_rigor": 0.25, 
            "industry_context": 0.20,
            "professional_presentation": 0.15,
            "citation_discipline": 0.15
        }
        
        self.rubrics = self._build_evaluation_rubrics()
    
    def _build_evaluation_rubrics(self) -> Dict[str, EvaluationRubric]:
        """Build comprehensive scoring rubrics for each quality dimension."""
        return {
            "strategic_narrative": EvaluationRubric(
                dimension_name="Strategic Narrative Quality",
                scoring_criteria={
                    "9-10": "Compelling investment thesis with clear storyline connecting company strategy, market dynamics, and financial projections. Rich contextual analysis that transforms numbers into coherent narrative.",
                    "7-8": "Well-developed investment story with good logical flow. Clear thesis statement with supporting narrative elements.",
                    "5-6": "Basic investment rationale present but limited storytelling. Some attempt to connect strategy and numbers.",
                    "3-4": "Minimal narrative development. Largely numbers-focused with limited strategic context or story flow.",
                    "1-2": "No coherent investment story. Pure data presentation without narrative integration."
                },
                weight=0.25
            ),
            "analytical_rigor": EvaluationRubric(
                dimension_name="Analytical Rigor",
                scoring_criteria={
                    "9-10": "Deep analytical depth with multiple data sources, sensitivity analysis, scenario planning, and thorough risk assessment. Evidence-based conclusions with robust methodology.",
                    "7-8": "Strong analytical foundation with good use of data, some sensitivity analysis, and well-supported conclusions.",
                    "5-6": "Adequate analysis with basic data interpretation and reasonable conclusions, but limited depth.",
                    "3-4": "Basic numerical presentation with minimal analytical interpretation or insight generation.",
                    "1-2": "No meaningful analysis. Raw data presentation without interpretation or conclusions."
                },
                weight=0.25
            ),
            "industry_context": EvaluationRubric(
                dimension_name="Industry Context Integration",
                scoring_criteria={
                    "9-10": "Comprehensive industry analysis with competitive positioning, market dynamics, regulatory environment, and macro-economic factors expertly integrated throughout.",
                    "7-8": "Good industry context with competitive analysis and market understanding informing the investment thesis.",
                    "5-6": "Basic industry background provided with some competitive context, but limited integration with analysis.",
                    "3-4": "Minimal industry context. Limited understanding of competitive landscape or market dynamics.",
                    "1-2": "No industry context or competitive analysis. Company analyzed in isolation."
                },
                weight=0.20
            ),
            "professional_presentation": EvaluationRubric(
                dimension_name="Professional Presentation",
                scoring_criteria={
                    "9-10": "Exceptional structure, flow, and readability. Professional formatting with effective use of charts, tables, and visual elements. Clear section organization and logical progression.",
                    "7-8": "Well-organized with good structure and readability. Appropriate use of visual elements and clear section breaks.",
                    "5-6": "Acceptable organization with basic structure. Some formatting issues but generally readable.",
                    "3-4": "Poor organization and structure. Difficult to follow with formatting problems and unclear sections.",
                    "1-2": "No clear structure or organization. Unreadable or unprofessional presentation."
                },
                weight=0.15
            ),
            "citation_discipline": EvaluationRubric(
                dimension_name="Citation & Evidence Discipline",
                scoring_criteria={
                    "9-10": "Exemplary citation discipline with all claims properly referenced. Strong integration of evidence from credible sources throughout the analysis.",
                    "7-8": "Good citation practices with most claims supported by references. Evidence well-integrated into analysis.",
                    "5-6": "Adequate referencing with basic evidence support, though some claims may lack proper citation.",
                    "3-4": "Poor citation discipline with many unsupported claims. Limited evidence integration.",
                    "1-2": "No proper citations or evidence discipline. Claims made without supporting references."
                },
                weight=0.15
            )
        }
    
    def evaluate_report(self, report_content: str, cassette_path: Optional[str] = None) -> ReportQualityResult:
        """
        Evaluate investment report quality across all dimensions.
        
        Args:
            report_content: Full text of the investment report to evaluate
            cassette_path: Optional path to LLM response cassette for deterministic testing
            
        Returns:
            ReportQualityResult with dimensional scores and overall assessment
        """
        if cassette_path:
            return self._evaluate_with_cassette(report_content, cassette_path)
        else:
            return self._evaluate_with_llm(report_content)
    
    def _evaluate_with_cassette(self, report_content: str, cassette_path: str) -> ReportQualityResult:
        """Load evaluation results from pre-recorded cassette for deterministic testing."""
        cassette_data = json.loads(Path(cassette_path).read_text())
        
        # Convert list of dimensions to QualityDimension objects
        dimensions = []
        for dim_data in cassette_data["dimensions"]:
            dimensions.append(QualityDimension(
                name=dim_data["name"],
                score=dim_data["score"],
                reasoning=dim_data["reasoning"],
                evidence=dim_data.get("evidence", []),
                improvement_suggestions=dim_data.get("improvement_suggestions", [])
            ))
        
        # Use overall score from cassette (already calculated with proper weights)
        overall_score = cassette_data.get("overall_score", 0.0)
        
        return ReportQualityResult(
            overall_score=overall_score,
            dimensions=dimensions,
            comparative_analysis=cassette_data.get("comparative_analysis"),
            recommendations=cassette_data.get("recommendations", []),
            metadata=cassette_data.get("metadata", {"evaluation_method": "cassette", "cassette_path": cassette_path})
        )
    
    def _evaluate_with_llm(self, report_content: str) -> ReportQualityResult:
        """Evaluate report using live LLM calls with professional investment analyst prompt."""
        
        # This would use the LLMProvider with deterministic parameters:
        # temperature=0, top_p=1, seed=2025
        
        prompt = self._build_evaluation_prompt(report_content)
        
        # For now, raise error since live LLM calls should use cassettes in this system
        from investing_agent.llm.provider import LLMProvider
        
        provider = LLMProvider()
        
        try:
            response = provider.call(
                model_id="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": prompt}],
                params={"temperature": 0, "top_p": 1, "seed": 2025}
            )
            
            # Parse structured response and build ReportQualityResult
            return self._parse_llm_response(response)
            
        except NotImplementedError:
            raise RuntimeError("Live LLM evaluation requires cassette_path for deterministic testing")
    
    def _build_evaluation_prompt(self, report_content: str) -> str:
        """Build comprehensive evaluation prompt for LLM judge."""
        
        rubric_details = ""
        for dim_name, rubric in self.rubrics.items():
            rubric_details += f"\n## {rubric.dimension_name} ({int(rubric.weight*100)}% weight)\n"
            for score_range, criteria in rubric.scoring_criteria.items():
                rubric_details += f"**{score_range}:** {criteria}\n"
        
        return f"""You are a senior investment research analyst evaluating the quality of an investment report. 

Your task is to assess this report across 5 dimensions using a 10-point scale, then provide an overall weighted score and actionable recommendations.

## EVALUATION RUBRIC
{rubric_details}

## BENCHMARK CONTEXT
- **HIGH QUALITY (9-10)**: Reports like our BYD benchmark that tell compelling investment stories with rich narrative, comprehensive analysis, professional presentation, and strong evidence discipline
- **LOW QUALITY (3-4)**: Reports like our META baseline that are primarily numbers-focused with minimal storytelling, limited context, and poor evidence integration

## REPORT TO EVALUATE:

{report_content}

## REQUIRED OUTPUT FORMAT:

Provide your evaluation in this exact JSON structure:

```json
{{
  "dimensions": {{
    "strategic_narrative": {{
      "score": 0.0,
      "reasoning": "Detailed explanation of score",
      "evidence": ["Specific examples from report"],
      "improvement_suggestions": ["Actionable recommendations"]
    }},
    "analytical_rigor": {{
      "score": 0.0,
      "reasoning": "Detailed explanation of score", 
      "evidence": ["Specific examples from report"],
      "improvement_suggestions": ["Actionable recommendations"]
    }},
    "industry_context": {{
      "score": 0.0,
      "reasoning": "Detailed explanation of score",
      "evidence": ["Specific examples from report"], 
      "improvement_suggestions": ["Actionable recommendations"]
    }},
    "professional_presentation": {{
      "score": 0.0,
      "reasoning": "Detailed explanation of score",
      "evidence": ["Specific examples from report"],
      "improvement_suggestions": ["Actionable recommendations"] 
    }},
    "citation_discipline": {{
      "score": 0.0,
      "reasoning": "Detailed explanation of score",
      "evidence": ["Specific examples from report"],
      "improvement_suggestions": ["Actionable recommendations"]
    }}
  }},
  "comparative_analysis": "How this report compares to high-quality benchmarks",
  "recommendations": ["Top 3-5 high-level improvements to transform this report"]
}}
```

Focus on being precise, actionable, and calibrated against professional investment research standards."""
    
    def _parse_llm_response(self, response: Dict) -> ReportQualityResult:
        """Parse LLM response into structured ReportQualityResult."""
        # This would parse the JSON response from the LLM
        # For now, stub implementation
        raise NotImplementedError("LLM response parsing not implemented - use cassettes")


# Convenience function for evaluation harness integration
def evaluate_report_quality(report_content: str, cassette_path: Optional[str] = None) -> ReportQualityResult:
    """
    Evaluate investment report quality using professional analyst judge.
    
    Args:
        report_content: Full text of investment report
        cassette_path: Optional cassette for deterministic evaluation
        
    Returns:
        ReportQualityResult with comprehensive quality assessment
    """
    judge = ReportQualityJudge()
    return judge.evaluate_report(report_content, cassette_path)