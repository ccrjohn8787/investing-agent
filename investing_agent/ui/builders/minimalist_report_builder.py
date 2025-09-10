"""Minimalist HTML Report Builder for Investment Reports."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV

logger = logging.getLogger(__name__)


class MinimalistReportBuilder:
    """Generates clean, minimalist HTML reports focused on readability and data presentation."""
    
    def __init__(self):
        """Initialize the minimalist report builder."""
        self.template_path = Path(__file__).parent.parent / "templates" / "minimalist_report.html"
        
    def build(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        narratives: Optional[Dict[str, str]] = None,
        evaluation: Optional[Any] = None,
        evidence: Optional[List[Dict]] = None,
        current_price: Optional[float] = None,
    ) -> str:
        """
        Build a minimalist HTML report.
        
        Args:
            inputs: Valuation inputs
            valuation: Valuation results
            narratives: Narrative sections
            evaluation: Evaluation scores (can be dict or object)
            evidence: Evidence and citations
            current_price: Current market price
            
        Returns:
            HTML string of the complete report
        """
        # Load template
        template = self._load_template()
        
        # Prepare all data
        data = self._prepare_data(inputs, valuation, narratives, evaluation, evidence, current_price)
        
        # Replace placeholders
        html = self._render_template(template, data)
        
        return html
    
    def _prepare_data(
        self,
        inputs: InputsI,
        valuation: ValuationV,
        narratives: Optional[Dict[str, str]],
        evaluation: Optional[Any],
        evidence: Optional[List[Dict]],
        current_price: Optional[float],
    ) -> Dict[str, Any]:
        """Prepare all data for template rendering."""
        
        # Calculate key metrics
        fair_value = valuation.value_per_share
        current_price = current_price or fair_value * 0.9
        upside = ((fair_value - current_price) / current_price) * 100
        
        # Determine rating and styling
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
        
        # Build detailed projections
        projections_data, terminal_value, total_ev = self._build_detailed_projections(inputs, valuation)
        projections_html = self._format_projections_table(projections_data)
        
        # Build sensitivity analysis
        sensitivity_data = self._build_sensitivity_analysis(inputs, valuation)
        sensitivity_headers, sensitivity_rows = self._format_sensitivity_table(sensitivity_data, fair_value)
        
        # Process evaluation scores
        scores = self._process_evaluation_scores(evaluation)
        
        # Format evidence
        evidence_html = self._format_evidence(evidence)
        
        # Format narratives
        narratives = narratives or {}
        
        # Calculate enterprise value
        enterprise_value = valuation.pv_explicit + valuation.pv_terminal
        
        return {
            # Company info
            "company": inputs.company,
            "ticker": inputs.ticker,
            "date": datetime.now().strftime("%B %d, %Y"),
            
            # Key metrics
            "current_price": f"{current_price:.2f}",
            "fair_value": f"{fair_value:.2f}",
            "upside": f"{upside:+.1f}",
            "upside_class": upside_class,
            "rating": rating,
            
            # Valuation metrics
            "revenue": f"{inputs.revenue_t0 / 1e9:.1f}",
            "revenue_growth": f"{inputs.drivers.sales_growth[0] * 100:.1f}",
            "operating_margin": f"{inputs.drivers.oper_margin[0] * 100:.1f}",
            "wacc": f"{inputs.wacc[0] * 100:.1f}",
            "terminal_growth": f"{inputs.drivers.stable_growth * 100:.1f}",
            "enterprise_value": f"{enterprise_value / 1e9:.1f}",
            
            # Projections
            "projections_rows": projections_html,
            "terminal_value": f"{terminal_value / 1e6:.0f}",
            "total_enterprise_value": f"{total_ev / 1e6:.0f}",
            
            # Sensitivity
            "sensitivity_margin_headers": sensitivity_headers,
            "sensitivity_rows": sensitivity_rows,
            
            # Quality scores
            "overall_score": scores["overall"],
            "narrative_score": scores["narrative"],
            "analytical_score": scores["analytical"],
            "industry_score": scores["industry"],
            "presentation_score": scores["presentation"],
            "citation_score": scores["citation"],
            
            # Narratives
            "executive_summary": self._format_narrative(narratives.get("executive_summary", 
                "Executive summary not available.")),
            "financial_analysis": self._format_narrative(narratives.get("financial_analysis", 
                "Financial analysis not available.")),
            "investment_thesis": self._format_narrative(narratives.get("investment_thesis", 
                "Investment thesis not available.")),
            "risk_analysis": self._format_narrative(narratives.get("risk_analysis", 
                "Risk analysis not available.")),
            "industry_context": self._format_narrative(narratives.get("industry_context", 
                "Industry context not available.")),
            "conclusion": self._format_narrative(narratives.get("conclusion", 
                "Investment conclusion not available.")),
            
            # Evidence
            "evidence_items": evidence_html,
        }
    
    def _build_detailed_projections(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> tuple[List[Dict], float, float]:
        """Build detailed year-by-year projections."""
        projections = []
        
        T = len(inputs.drivers.sales_growth)
        revenue = inputs.revenue_t0
        tax_rate = inputs.tax_rate
        
        total_pv_explicit = 0
        
        for t in range(min(T, 10)):  # Show up to 10 years
            # Growth and margin for this year
            growth = inputs.drivers.sales_growth[t]
            margin = inputs.drivers.oper_margin[t]
            
            # Calculate revenue
            revenue = revenue * (1 + growth)
            
            # Calculate EBIT
            ebit = revenue * margin
            
            # Calculate tax
            tax = ebit * tax_rate
            
            # Calculate NOPAT
            nopat = ebit * (1 - tax_rate)
            
            # Calculate reinvestment
            if t < len(inputs.sales_to_capital):
                s2c = inputs.sales_to_capital[t]
            else:
                s2c = inputs.sales_to_capital[-1]
            
            # Reinvestment rate based on growth and sales-to-capital
            if s2c > 0:
                reinvestment_rate = growth / s2c
            else:
                reinvestment_rate = 0
            
            reinvestment = nopat * reinvestment_rate
            
            # Calculate FCFF
            fcff = nopat - reinvestment
            
            # Calculate present value
            wacc = inputs.wacc[t] if t < len(inputs.wacc) else inputs.wacc[-1]
            discount_factor = (1 + wacc) ** -(t + 1)
            pv = fcff * discount_factor
            
            total_pv_explicit += pv
            
            projections.append({
                "year": t + 1,
                "revenue": revenue / 1e6,  # In millions
                "growth": growth * 100,
                "margin": margin * 100,
                "ebit": ebit / 1e6,
                "tax": tax / 1e6,
                "nopat": nopat / 1e6,
                "reinvestment": reinvestment / 1e6,
                "fcff": fcff / 1e6,
                "pv": pv / 1e6,
            })
        
        # Terminal value
        terminal_value = valuation.pv_terminal
        total_ev = valuation.pv_explicit + valuation.pv_terminal
        
        return projections, terminal_value, total_ev
    
    def _format_projections_table(self, projections: List[Dict]) -> str:
        """Format projections data as HTML table rows."""
        rows = []
        for proj in projections:
            row = f"""
            <tr>
                <td class="center">{proj['year']}</td>
                <td class="number">{proj['revenue']:.0f}</td>
                <td class="number">{proj['growth']:.1f}</td>
                <td class="number">{proj['margin']:.1f}</td>
                <td class="number">{proj['ebit']:.0f}</td>
                <td class="number">{proj['tax']:.0f}</td>
                <td class="number">{proj['nopat']:.0f}</td>
                <td class="number">{proj['reinvestment']:.0f}</td>
                <td class="number">{proj['fcff']:.0f}</td>
                <td class="number">{proj['pv']:.0f}</td>
            </tr>"""
            rows.append(row)
        return "".join(rows)
    
    def _build_sensitivity_analysis(
        self, 
        inputs: InputsI, 
        valuation: ValuationV
    ) -> Dict[tuple, float]:
        """Build sensitivity analysis grid."""
        from investing_agent.kernels.ginzu import value as kernel_value
        
        sensitivity = {}
        base_value = valuation.value_per_share
        
        # Define ranges
        growth_variations = [-0.05, -0.025, 0, 0.025, 0.05]  # -5% to +5%
        margin_variations = [-0.02, -0.01, 0, 0.01, 0.02]    # -2% to +2%
        
        base_growth = inputs.drivers.sales_growth[0]
        base_margin = inputs.drivers.oper_margin[0]
        
        for growth_delta in growth_variations:
            for margin_delta in margin_variations:
                # Create modified inputs
                new_growth = base_growth + growth_delta
                new_margin = base_margin + margin_delta
                
                # Ensure reasonable bounds
                new_growth = max(0, min(0.5, new_growth))
                new_margin = max(0.01, min(0.5, new_margin))
                
                # Create modified drivers
                modified_drivers = inputs.drivers.model_copy()
                modified_drivers.sales_growth = [new_growth] + list(inputs.drivers.sales_growth[1:])
                modified_drivers.oper_margin = [new_margin] + list(inputs.drivers.oper_margin[1:])
                
                # Calculate new valuation
                try:
                    # Create modified inputs
                    modified_inputs = inputs.model_copy()
                    modified_inputs.drivers = modified_drivers
                    
                    new_valuation = kernel_value(modified_inputs)
                    sensitivity[(new_growth, new_margin)] = new_valuation.value_per_share
                except:
                    sensitivity[(new_growth, new_margin)] = base_value
        
        return sensitivity
    
    def _format_sensitivity_table(
        self, 
        sensitivity: Dict[tuple, float],
        base_value: float
    ) -> tuple[str, str]:
        """Format sensitivity analysis as HTML table."""
        # Get unique growth and margin values
        growths = sorted(set(k[0] for k in sensitivity.keys()))
        margins = sorted(set(k[1] for k in sensitivity.keys()))
        
        # Build headers
        headers = "".join([f"<th class='number'>{m*100:.0f}%</th>" for m in margins])
        
        # Build rows
        rows = []
        for growth in growths:
            cells = [f"<td>{growth*100:.0f}%</td>"]
            for margin in margins:
                value = sensitivity.get((growth, margin), 0)
                # Highlight if close to base value
                if abs(value - base_value) < 0.5:
                    cells.append(f"<td class='number highlight'>${value:.2f}</td>")
                else:
                    cells.append(f"<td class='number'>${value:.2f}</td>")
            rows.append(f"<tr>{''.join(cells)}</tr>")
        
        return headers, "".join(rows)
    
    def _process_evaluation_scores(self, evaluation: Optional[Any]) -> Dict[str, str]:
        """Process evaluation scores from dict or object."""
        default_scores = {
            "overall": "N/A",
            "narrative": "N/A",
            "analytical": "N/A",
            "industry": "N/A",
            "presentation": "N/A",
            "citation": "N/A",
        }
        
        if not evaluation:
            return default_scores
        
        try:
            if isinstance(evaluation, dict):
                # Handle dict format
                overall = evaluation.get('overall_score', 0)
                dimensions = {}
                for d in evaluation.get('dimensional_scores', []):
                    dim_name = d.get('dimension', '')
                    if 'narrative' in dim_name.lower():
                        dimensions['narrative'] = d.get('score', 0)
                    elif 'analytical' in dim_name.lower():
                        dimensions['analytical'] = d.get('score', 0)
                    elif 'industry' in dim_name.lower():
                        dimensions['industry'] = d.get('score', 0)
                    elif 'presentation' in dim_name.lower():
                        dimensions['presentation'] = d.get('score', 0)
                    elif 'citation' in dim_name.lower():
                        dimensions['citation'] = d.get('score', 0)
            else:
                # Handle object format
                overall = evaluation.overall_score
                dimensions = {}
                for d in evaluation.dimensional_scores:
                    if 'narrative' in d.dimension.lower():
                        dimensions['narrative'] = d.score
                    elif 'analytical' in d.dimension.lower():
                        dimensions['analytical'] = d.score
                    elif 'industry' in d.dimension.lower():
                        dimensions['industry'] = d.score
                    elif 'presentation' in d.dimension.lower():
                        dimensions['presentation'] = d.score
                    elif 'citation' in d.dimension.lower():
                        dimensions['citation'] = d.score
            
            return {
                "overall": f"{overall:.1f}",
                "narrative": f"{dimensions.get('narrative', 0):.1f}",
                "analytical": f"{dimensions.get('analytical', 0):.1f}",
                "industry": f"{dimensions.get('industry', 0):.1f}",
                "presentation": f"{dimensions.get('presentation', 0):.1f}",
                "citation": f"{dimensions.get('citation', 0):.1f}",
            }
        except Exception as e:
            logger.warning(f"Error processing evaluation scores: {e}")
            return default_scores
    
    def _format_evidence(self, evidence: Optional[List[Dict]]) -> str:
        """Format evidence items as HTML."""
        if not evidence:
            return "<li class='evidence-item'>No evidence available.</li>"
        
        items = []
        for item in evidence[:10]:  # Limit to 10 items
            confidence = item.get("confidence", 0.5)
            if confidence > 0.8:
                conf_class = "confidence-high"
                conf_text = "High"
            elif confidence > 0.6:
                conf_class = "confidence-medium"
                conf_text = "Medium"
            else:
                conf_class = "confidence-low"
                conf_text = "Low"
            
            html = f"""
            <li class="evidence-item">
                <div class="evidence-quote">"{item.get('quote', 'No quote available')}"</div>
                <div class="evidence-source">
                    Source: {item.get('source_name', 'Unknown')}
                    <span class="evidence-confidence {conf_class}">
                        {conf_text} ({int(confidence * 100)}%)
                    </span>
                </div>
            </li>"""
            items.append(html)
        
        return "".join(items)
    
    def _format_narrative(self, text: str) -> str:
        """Format narrative text, preserving paragraphs."""
        # Simple paragraph formatting
        paragraphs = text.split('\n\n')
        formatted = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # Check if it's a list item
                if para.startswith('- ') or para.startswith('• '):
                    # Convert to HTML list
                    items = para.split('\n')
                    list_html = "<ul>"
                    for item in items:
                        item = item.strip('- •').strip()
                        if item:
                            list_html += f"<li>{item}</li>"
                    list_html += "</ul>"
                    formatted.append(list_html)
                else:
                    formatted.append(f"<p>{para}</p>")
        
        return "\n".join(formatted)
    
    def _load_template(self) -> str:
        """Load the HTML template."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Replace template placeholders with data."""
        html = template
        
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            html = html.replace(placeholder, str(value))
        
        return html
    
    def save_report(self, html: str, output_path: Path) -> Path:
        """
        Save the HTML report to a file.
        
        Args:
            html: HTML content
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Minimalist report saved to: {output_path}")
        return output_path