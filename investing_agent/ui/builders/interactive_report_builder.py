"""Interactive HTML Report Builder for Investment Reports."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evaluation_metrics import EvaluationResult, EvaluationScore

logger = logging.getLogger(__name__)


class InteractiveReportBuilder:
    """Generates interactive HTML reports from valuation and narrative data."""
    
    def __init__(self):
        """Initialize the report builder."""
        self.template_path = Path(__file__).parent.parent / "templates" / "report.html"
        
    def build(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        narratives: Optional[Dict[str, str]] = None,
        evaluation: Optional[Any] = None,  # Can be EvaluationResult or dict
        evidence: Optional[List[Dict]] = None,
        current_price: Optional[float] = None,
    ) -> str:
        """
        Build an interactive HTML report.
        
        Args:
            inputs: Valuation inputs
            valuation: Valuation results
            narratives: Narrative sections (executive_summary, financial_analysis, etc.)
            evaluation: Evaluation scores
            evidence: Evidence and citations
            current_price: Current market price
            
        Returns:
            HTML string of the complete report
        """
        # Prepare data for template
        data = self._prepare_data(inputs, valuation, narratives, evaluation, evidence, current_price)
        
        # Load template
        template = self._load_template()
        
        # Replace placeholders
        html = self._render_template(template, data)
        
        # Embed JSON data for JavaScript
        html = self._embed_json_data(html, data)
        
        return html
    
    def _prepare_data(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        narratives: Optional[Dict[str, str]],
        evaluation: Optional[EvaluationResult],
        evidence: Optional[List[Dict]],
        current_price: Optional[float],
    ) -> Dict[str, Any]:
        """Prepare data for template rendering."""
        
        # Calculate metrics
        fair_value = valuation.value_per_share
        current_price = current_price or fair_value * 0.9  # Default to 10% discount
        upside = ((fair_value - current_price) / current_price) * 100
        
        # Determine rating
        if upside > 20:
            rating = "STRONG BUY"
            upside_class = "positive"
        elif upside > 10:
            rating = "BUY"
            upside_class = "positive"
        elif upside > -10:
            rating = "HOLD"
            upside_class = ""
        else:
            rating = "SELL"
            upside_class = "negative"
        
        # Evaluation scores (handle both object and dict)
        if evaluation:
            if isinstance(evaluation, dict):
                overall_score = f"{evaluation.get('overall_score', 0):.1f}"
                score_class = self._get_score_class(evaluation.get('overall_score', 0))
                
                # Extract dimensional scores from dict
                dimensions = {}
                for d in evaluation.get('dimensional_scores', []):
                    dimensions[d.get('dimension', '')] = d.get('score', 0)
            else:
                # Assume it's an EvaluationResult object
                overall_score = f"{evaluation.overall_score:.1f}"
                score_class = self._get_score_class(evaluation.overall_score)
                
                # Extract dimensional scores from object
                dimensions = {d.dimension: d.score for d in evaluation.dimensional_scores}
            
            narrative_score = dimensions.get("strategic_narrative", 0)
            analytical_score = dimensions.get("analytical_rigor", 0)
            industry_score = dimensions.get("industry_context", 0)
            presentation_score = dimensions.get("professional_presentation", 0)
            citation_score = dimensions.get("citation_discipline", 0)
        else:
            overall_score = "N/A"
            score_class = ""
            narrative_score = analytical_score = industry_score = 0
            presentation_score = citation_score = 0
        
        # Build projections table data
        projections = self._build_projections_data(inputs, valuation)
        
        # Prepare chart data for visualization
        chart_years = list(range(1, min(6, len(inputs.drivers.sales_growth) + 1)))
        chart_revenue = []
        chart_margin = []
        revenue = inputs.revenue_t0
        for i, year in enumerate(chart_years):
            if i < len(inputs.drivers.sales_growth):
                revenue = revenue * (1 + inputs.drivers.sales_growth[i])
                chart_revenue.append(revenue / 1e9)  # Convert to billions
                chart_margin.append(inputs.drivers.oper_margin[i] * 100 if i < len(inputs.drivers.oper_margin) else inputs.drivers.stable_margin * 100)
            else:
                revenue = revenue * (1 + inputs.drivers.stable_growth)
                chart_revenue.append(revenue / 1e9)
                chart_margin.append(inputs.drivers.stable_margin * 100)
        
        # Prepare evidence
        evidence_data = self._prepare_evidence(evidence) if evidence else []
        
        # Format narratives with fallbacks
        narratives = narratives or {}
        
        return {
            # Company info
            "company": inputs.company,
            "ticker": inputs.ticker,
            "fair_value": f"{fair_value:.2f}",
            "current_price": f"{current_price:.2f}",
            "upside": f"{upside:.1f}",
            "upside_class": upside_class,
            "rating": rating,
            
            # Key metrics
            "revenue": f"{inputs.revenue_t0 / 1e9:.1f}",
            "revenue_growth": f"{inputs.drivers.sales_growth[0] * 100:.1f}",
            "operating_margin": f"{inputs.drivers.oper_margin[0] * 100:.1f}",
            "margin_trend": "Expanding" if len(inputs.drivers.oper_margin) > 1 and inputs.drivers.oper_margin[1] > inputs.drivers.oper_margin[0] else "Stable",
            "wacc": f"{inputs.wacc[0] * 100:.1f}",
            "roic": f"{inputs.drivers.oper_margin[0] * (1 - inputs.tax_rate) * inputs.sales_to_capital[0] * 100:.1f}",
            
            # Evaluation scores
            "overall_score": overall_score,
            "score_class": score_class,
            "narrative_score": f"{narrative_score:.1f}",
            "narrative_pct": narrative_score * 10,
            "analytical_score": f"{analytical_score:.1f}",
            "analytical_pct": analytical_score * 10,
            "industry_score": f"{industry_score:.1f}",
            "industry_pct": industry_score * 10,
            "presentation_score": f"{presentation_score:.1f}",
            "presentation_pct": presentation_score * 10,
            "citation_score": f"{citation_score:.1f}",
            "citation_pct": citation_score * 10,
            
            # DCF assumptions
            "default_growth": f"{inputs.drivers.sales_growth[0] * 100:.1f}",
            "default_margin": f"{inputs.drivers.oper_margin[0] * 100:.1f}",
            "default_wacc": f"{inputs.wacc[0] * 100:.1f}",
            "default_terminal": f"{inputs.drivers.stable_growth * 100:.1f}",
            
            # Scenario values
            "bear_value": f"{fair_value * 0.75:.2f}",  # 25% discount for bear case
            "bear_growth": f"{max(0, inputs.drivers.sales_growth[0] * 100 - 5):.1f}",
            "bear_margin": f"{max(10, inputs.drivers.oper_margin[0] * 100 - 5):.1f}",
            "bull_value": f"{fair_value * 1.30:.2f}",  # 30% premium for bull case
            "bull_growth": f"{inputs.drivers.sales_growth[0] * 100 + 5:.1f}",
            "bull_margin": f"{min(50, inputs.drivers.oper_margin[0] * 100 + 5):.1f}",
            
            # Narratives
            "executive_summary": self._format_narrative(narratives.get("executive_summary", "Executive summary not available.")),
            "financial_analysis": self._format_narrative(narratives.get("financial_analysis", "Financial analysis not available.")),
            "investment_thesis": self._format_narrative(narratives.get("investment_thesis", "Investment thesis not available.")),
            "risk_analysis": self._format_narrative(narratives.get("risk_analysis", "Risk analysis not available.")),
            
            # JSON data for JavaScript
            "json_data": {
                "company": inputs.company,
                "ticker": inputs.ticker,
                "valuation": {
                    "fair_value": fair_value,
                    "pv_explicit": valuation.pv_explicit,
                    "pv_terminal": valuation.pv_terminal,
                },
                "assumptions": {
                    "growth": inputs.drivers.sales_growth[0] * 100,
                    "margin": inputs.drivers.oper_margin[0] * 100,
                    "wacc": inputs.wacc[0] * 100,
                    "terminal_growth": inputs.drivers.stable_growth * 100,
                },
                "current_price": current_price,
                "upside": upside,
                "projections": projections,
                "evidence": evidence_data,
                "charts": {
                    "years": [f"Year {y}" for y in chart_years],
                    "revenue": chart_revenue,
                    "margin": chart_margin,
                    "fcf": [float(p.get("fcff", "0M").replace("M", "").replace("$", "")) if p.get("fcff") else 0 for p in projections[:5]] if projections else [],
                },
                "evaluation": {
                    "overall_score": (
                        evaluation.get('overall_score', 0) if isinstance(evaluation, dict) 
                        else evaluation.overall_score if evaluation 
                        else 0
                    ),
                    "dimensions": (
                        [{"name": d.get('dimension', ''), "score": d.get('score', 0)} 
                         for d in evaluation.get('dimensional_scores', [])]
                        if isinstance(evaluation, dict)
                        else [{"name": d.dimension, "score": d.score} 
                              for d in (evaluation.dimensional_scores if evaluation else [])]
                    ),
                },
            },
        }
    
    def _get_score_class(self, score: float) -> str:
        """Get CSS class for score color coding."""
        if score >= 9:
            return "score-excellent"
        elif score >= 7:
            return "score-good"
        elif score >= 5:
            return "score-fair"
        else:
            return "score-poor"
    
    def _build_projections_data(self, inputs: InputsI, valuation: ValuationV) -> List[Dict]:
        """Build projections table data."""
        projections = []
        
        # Get drivers
        T = len(inputs.drivers.sales_growth)
        revenue_t0 = inputs.revenue_t0
        
        # Calculate year-by-year projections
        revenue = revenue_t0
        for t in range(T):
            growth = inputs.drivers.sales_growth[t]
            margin = inputs.drivers.oper_margin[t]
            
            # Simple approximation of FCFF
            revenue = revenue * (1 + growth)
            ebit = revenue * margin
            nopat = ebit * (1 - inputs.tax_rate)
            
            # Approximate FCFF (simplified)
            reinvestment_rate = growth / (inputs.sales_to_capital[t] if t < len(inputs.sales_to_capital) else inputs.sales_to_capital[-1])
            fcff = nopat * (1 - reinvestment_rate)
            
            # Discount factor
            wacc = inputs.wacc[t] if t < len(inputs.wacc) else inputs.wacc[-1]
            df = (1 + wacc) ** -(t + 1)
            pv = fcff * df
            
            projections.append({
                "year": t + 1,
                "revenue": f"{revenue / 1e6:.0f}M",
                "growth": f"{growth * 100:.1f}",
                "margin": f"{margin * 100:.1f}",
                "fcff": f"{fcff / 1e6:.0f}M",
                "pv": f"{pv / 1e6:.0f}M",
            })
        
        return projections
    
    def _prepare_evidence(self, evidence: List[Dict]) -> List[Dict]:
        """Prepare evidence data for display."""
        evidence_data = []
        
        for item in evidence[:10]:  # Limit to top 10
            confidence = item.get("confidence", 0.5)
            if confidence > 0.8:
                confidence_level = "high"
            elif confidence > 0.6:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            
            evidence_data.append({
                "quote": item.get("quote", ""),
                "source": item.get("source_url", "#"),
                "source_name": item.get("source_name", "Source"),
                "confidence": int(confidence * 100),
                "confidence_level": confidence_level,
            })
        
        return evidence_data
    
    def _format_narrative(self, text: str) -> str:
        """Format narrative text for HTML display."""
        # Convert markdown-style formatting to HTML
        text = text.replace("\n\n", "</p><p>")
        text = f"<p>{text}</p>"
        
        # Convert markdown bold to HTML
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        
        # Convert bullet points
        text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.DOTALL)
        
        return text
    
    def _load_template(self) -> str:
        """Load the HTML template."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Replace template placeholders with data."""
        html = template
        
        # Replace simple placeholders
        for key, value in data.items():
            if key != "json_data":  # Skip JSON data for now
                placeholder = f"{{{{{key}}}}}"
                html = html.replace(placeholder, str(value))
        
        return html
    
    def _embed_json_data(self, html: str, data: Dict[str, Any]) -> str:
        """Embed JSON data for JavaScript consumption."""
        json_str = json.dumps(data["json_data"], indent=2)
        placeholder = "{{json_data}}"
        return html.replace(placeholder, json_str)
    
    def save_report(
        self,
        html: str,
        output_path: Path,
        include_chart_js: bool = True,
        include_app_js: bool = True
    ) -> Path:
        """
        Save the HTML report to a file.
        
        Args:
            html: HTML content
            output_path: Output file path
            include_chart_js: Whether to include Chart.js library
            
        Returns:
            Path to saved file
        """
        # Embed JavaScript libraries and app code
        scripts = []
        
        if include_chart_js:
            scripts.append('''
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>''')
        
        if include_app_js:
            # Read and embed our custom JS files
            js_dir = Path(__file__).parent.parent / "static" / "js"
            
            # Embed charts.js if it exists
            charts_js_path = js_dir / "charts.js"
            if charts_js_path.exists():
                with open(charts_js_path, 'r') as f:
                    charts_js = f.read()
                scripts.append(f'''
    <!-- Charts Module -->
    <script>
    {charts_js}
    </script>''')
            
            # Embed export.js if it exists
            export_js_path = js_dir / "export.js"
            if export_js_path.exists():
                with open(export_js_path, 'r') as f:
                    export_js = f.read()
                scripts.append(f'''
    <!-- Export Module -->
    <script>
    {export_js}
    </script>''')
            
            # Embed app.js if it exists
            app_js_path = js_dir / "app.js"
            if app_js_path.exists():
                with open(app_js_path, 'r') as f:
                    app_js = f.read()
                scripts.append(f'''
    <!-- Main Application -->
    <script>
    {app_js}
    </script>''')
        
        # Insert all scripts before </body>
        if scripts:
            scripts_html = '\n'.join(scripts)
            html = html.replace("</body>", f"{scripts_html}\n</body>")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Interactive report saved to: {output_path}")
        return output_path