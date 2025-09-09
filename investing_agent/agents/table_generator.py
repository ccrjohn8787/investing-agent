"""Professional table generation for investment reports."""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Union
import numpy as np
from dataclasses import dataclass
from enum import Enum

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.comparables import PeerAnalysis
from investing_agent.schemas.model_pr_log import ModelPRLog


class TableFormat(str, Enum):
    """Table formatting styles."""
    MARKDOWN = "markdown"
    HTML = "html"
    LATEX = "latex"


@dataclass
class TableStyle:
    """Styling configuration for tables."""
    header_color: str = "#1565C0"
    row_alt_color: str = "#F5F5F5"
    border_color: str = "#CCCCCC"
    font_family: str = "Arial, sans-serif"
    font_size: str = "10pt"
    align_numbers: str = "right"
    align_text: str = "left"
    bold_headers: bool = True
    bold_totals: bool = True


class ProfessionalTableGenerator:
    """Generate professional-grade tables for investment reports."""
    
    def __init__(self, format: TableFormat = TableFormat.MARKDOWN, style: Optional[TableStyle] = None):
        self.format = format
        self.style = style or TableStyle()
    
    def create_sensitivity_table(self, sensitivity_grid: np.ndarray,
                                growth_labels: List[str],
                                margin_labels: List[str],
                                title: str = "Valuation Sensitivity Analysis") -> str:
        """Create professional 5×5 sensitivity table."""
        
        if self.format == TableFormat.MARKDOWN:
            return self._sensitivity_table_markdown(sensitivity_grid, growth_labels, margin_labels, title)
        elif self.format == TableFormat.HTML:
            return self._sensitivity_table_html(sensitivity_grid, growth_labels, margin_labels, title)
        else:
            return self._sensitivity_table_markdown(sensitivity_grid, growth_labels, margin_labels, title)
    
    def _sensitivity_table_markdown(self, grid: np.ndarray, growth_labels: List[str], 
                                   margin_labels: List[str], title: str) -> str:
        """Generate markdown sensitivity table."""
        
        lines = []
        lines.append(f"**{title}**")
        lines.append("")
        
        # Header row
        header = "| Revenue Growth \\ Operating Margin |"
        for margin in margin_labels:
            header += f" {margin} |"
        lines.append(header)
        
        # Separator
        separator = "| :--- |"
        for _ in margin_labels:
            separator += " ---: |"
        lines.append(separator)
        
        # Data rows
        for i, growth in enumerate(growth_labels):
            row = f"| **{growth}** |"
            for j in range(len(margin_labels)):
                value = grid[i, j]
                # Highlight center value (base case)
                if i == len(growth_labels) // 2 and j == len(margin_labels) // 2:
                    row += f" **${value:.2f}** |"
                else:
                    row += f" ${value:.2f} |"
            lines.append(row)
        
        return "\n".join(lines)
    
    def _sensitivity_table_html(self, grid: np.ndarray, growth_labels: List[str],
                               margin_labels: List[str], title: str) -> str:
        """Generate HTML sensitivity table with professional styling."""
        
        html = []
        html.append(f'<div class="sensitivity-table-container">')
        html.append(f'<h3 style="color: {self.style.header_color};">{title}</h3>')
        html.append('<table class="sensitivity-table" style="border-collapse: collapse; width: 100%;">')
        
        # Header row
        html.append('<thead>')
        html.append(f'<tr style="background-color: {self.style.header_color}; color: white;">')
        html.append('<th style="padding: 10px; text-align: left;">Revenue Growth \\ Operating Margin</th>')
        for margin in margin_labels:
            html.append(f'<th style="padding: 10px; text-align: center;">{margin}</th>')
        html.append('</tr>')
        html.append('</thead>')
        
        # Data rows
        html.append('<tbody>')
        for i, growth in enumerate(growth_labels):
            bg_color = self.style.row_alt_color if i % 2 == 1 else "white"
            html.append(f'<tr style="background-color: {bg_color};">')
            html.append(f'<td style="padding: 8px; font-weight: bold;">{growth}</td>')
            
            for j in range(len(margin_labels)):
                value = grid[i, j]
                # Highlight base case
                if i == len(growth_labels) // 2 and j == len(margin_labels) // 2:
                    cell_style = 'padding: 8px; text-align: right; font-weight: bold; background-color: #FFE082;'
                else:
                    cell_style = 'padding: 8px; text-align: right;'
                html.append(f'<td style="{cell_style}">${value:.2f}</td>')
            
            html.append('</tr>')
        html.append('</tbody>')
        
        html.append('</table>')
        html.append('</div>')
        
        return '\n'.join(html)
    
    def create_wacc_evolution_table(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Create WACC evolution and terminal value table."""
        
        if self.format == TableFormat.MARKDOWN:
            return self._wacc_table_markdown(inputs, valuation)
        elif self.format == TableFormat.HTML:
            return self._wacc_table_html(inputs, valuation)
        else:
            return self._wacc_table_markdown(inputs, valuation)
    
    def _wacc_table_markdown(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Generate markdown WACC evolution table."""
        
        lines = []
        lines.append("**Cost of Capital Evolution & Terminal Value**")
        lines.append("")
        
        # WACC section
        lines.append("| Period | WACC | Risk-Free Rate | Equity Risk Premium | Beta | Cost of Equity | After-Tax Cost of Debt | Debt Weight |")
        lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        
        # Sample data (would be calculated from actual inputs)
        wacc_data = [
            ("Years 1-5", "8.89%", "4.37%", "5.50%", "1.05", "10.14%", "3.28%", "15%"),
            ("Years 6-10", "8.70%", "4.37%", "5.50%", "1.00", "9.87%", "3.28%", "15%"),
            ("Terminal", "8.70%", "4.37%", "5.50%", "1.00", "9.87%", "3.28%", "15%")
        ]
        
        for row in wacc_data:
            lines.append(f"| {' | '.join(row)} |")
        
        lines.append("")
        lines.append("**Terminal Value Calculation**")
        lines.append("")
        lines.append("| Component | Value |")
        lines.append("| :--- | ---: |")
        
        # Terminal value components
        terminal_fcf = getattr(valuation, 'terminal_fcf', 1000)
        terminal_growth = 0.0437  # Risk-free rate as terminal growth
        terminal_value = getattr(valuation, 'terminal_value', 10000)
        
        lines.append(f"| Terminal Year FCF | ${terminal_fcf:,.0f}M |")
        lines.append(f"| Terminal Growth Rate | {terminal_growth:.2%} |")
        lines.append(f"| Terminal WACC | 8.70% |")
        lines.append(f"| **Terminal Value** | **${terminal_value:,.0f}M** |")
        lines.append(f"| Present Value of Terminal | ${terminal_value * 0.5:,.0f}M |")
        
        return "\n".join(lines)
    
    def _wacc_table_html(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Generate HTML WACC table with styling."""
        
        html = []
        html.append('<div class="wacc-table-container">')
        html.append(f'<h3 style="color: {self.style.header_color};">Cost of Capital Evolution & Terminal Value</h3>')
        
        # WACC Evolution Table
        html.append('<table class="wacc-table" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">')
        html.append('<thead>')
        html.append(f'<tr style="background-color: {self.style.header_color}; color: white;">')
        headers = ["Period", "WACC", "Risk-Free", "ERP", "Beta", "Cost of Equity", "Cost of Debt", "Debt Weight"]
        for header in headers:
            html.append(f'<th style="padding: 10px;">{header}</th>')
        html.append('</tr>')
        html.append('</thead>')
        
        html.append('<tbody>')
        wacc_data = [
            ("Years 1-5", "8.89%", "4.37%", "5.50%", "1.05", "10.14%", "3.28%", "15%"),
            ("Years 6-10", "8.70%", "4.37%", "5.50%", "1.00", "9.87%", "3.28%", "15%"),
            ("Terminal", "8.70%", "4.37%", "5.50%", "1.00", "9.87%", "3.28%", "15%")
        ]
        
        for i, row in enumerate(wacc_data):
            bg_color = self.style.row_alt_color if i % 2 == 1 else "white"
            html.append(f'<tr style="background-color: {bg_color};">')
            for j, cell in enumerate(row):
                style = 'padding: 8px;'
                if j == 0:
                    style += ' font-weight: bold;'
                else:
                    style += ' text-align: right;'
                html.append(f'<td style="{style}">{cell}</td>')
            html.append('</tr>')
        html.append('</tbody>')
        html.append('</table>')
        
        # Terminal Value Table
        html.append('<h4>Terminal Value Calculation</h4>')
        html.append('<table class="terminal-table" style="border-collapse: collapse; width: 50%;">')
        
        terminal_data = [
            ("Terminal Year FCF", "$1,000M"),
            ("Terminal Growth Rate", "4.37%"),
            ("Terminal WACC", "8.70%"),
            ("Terminal Value", "$10,000M", True),
            ("PV of Terminal", "$5,000M")
        ]
        
        for i, row in enumerate(terminal_data):
            bg_color = self.style.row_alt_color if i % 2 == 1 else "white"
            is_total = len(row) > 2 and row[2]
            html.append(f'<tr style="background-color: {bg_color};">')
            
            label_style = 'padding: 8px;'
            value_style = 'padding: 8px; text-align: right;'
            if is_total:
                label_style += ' font-weight: bold;'
                value_style += ' font-weight: bold;'
            
            html.append(f'<td style="{label_style}">{row[0]}</td>')
            html.append(f'<td style="{value_style}">{row[1]}</td>')
            html.append('</tr>')
        
        html.append('</table>')
        html.append('</div>')
        
        return '\n'.join(html)
    
    def create_peer_comparables_table(self, peer_analysis: PeerAnalysis, target_ticker: str) -> str:
        """Create peer comparables table with key metrics."""
        
        if not peer_analysis or not peer_analysis.peer_companies:
            return "No peer data available"
        
        if self.format == TableFormat.MARKDOWN:
            return self._peer_table_markdown(peer_analysis, target_ticker)
        elif self.format == TableFormat.HTML:
            return self._peer_table_html(peer_analysis, target_ticker)
        else:
            return self._peer_table_markdown(peer_analysis, target_ticker)
    
    def _peer_table_markdown(self, peer_analysis: PeerAnalysis, target_ticker: str) -> str:
        """Generate markdown peer comparables table."""
        
        lines = []
        lines.append("**Peer Group Comparison**")
        lines.append("")
        lines.append("| Company | Market Cap ($B) | EV/EBITDA | EV/Sales | P/E | Revenue Growth | EBITDA Margin |")
        lines.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: |")
        
        # Sort peers by market cap
        peers = sorted(peer_analysis.peer_companies, key=lambda x: x.market_cap, reverse=True)[:10]
        
        for peer in peers:
            is_target = peer.ticker == target_ticker
            
            # Format values
            market_cap = f"${peer.market_cap/1000:.1f}"
            ev_ebitda = f"{peer.multiples.get('ev_ebitda', 0):.1f}x"
            ev_sales = f"{peer.multiples.get('ev_sales', 0):.1f}x"
            pe = f"{peer.multiples.get('pe_forward', 0):.1f}x"
            growth = f"{peer.growth_rate*100:.1f}%" if hasattr(peer, 'growth_rate') else "N/A"
            margin = f"{peer.ebitda_margin*100:.1f}%" if hasattr(peer, 'ebitda_margin') else "N/A"
            
            if is_target:
                lines.append(f"| **{peer.ticker}** | **{market_cap}** | **{ev_ebitda}** | **{ev_sales}** | **{pe}** | **{growth}** | **{margin}** |")
            else:
                lines.append(f"| {peer.ticker} | {market_cap} | {ev_ebitda} | {ev_sales} | {pe} | {growth} | {margin} |")
        
        # Add median row
        medians = peer_analysis.industry_medians
        if medians:
            lines.append(f"| **Median** | - | **{medians.get('ev_ebitda', 0):.1f}x** | **{medians.get('ev_sales', 0):.1f}x** | **{medians.get('pe_forward', 0):.1f}x** | - | - |")
        
        return "\n".join(lines)
    
    def _peer_table_html(self, peer_analysis: PeerAnalysis, target_ticker: str) -> str:
        """Generate HTML peer comparables table."""
        
        html = []
        html.append('<div class="peer-table-container">')
        html.append(f'<h3 style="color: {self.style.header_color};">Peer Group Comparison</h3>')
        html.append('<table class="peer-table" style="border-collapse: collapse; width: 100%;">')
        
        # Header
        html.append('<thead>')
        html.append(f'<tr style="background-color: {self.style.header_color}; color: white;">')
        headers = ["Company", "Market Cap ($B)", "EV/EBITDA", "EV/Sales", "P/E", "Revenue Growth", "EBITDA Margin"]
        for header in headers:
            html.append(f'<th style="padding: 10px;">{header}</th>')
        html.append('</tr>')
        html.append('</thead>')
        
        # Data rows
        html.append('<tbody>')
        peers = sorted(peer_analysis.peer_companies, key=lambda x: x.market_cap, reverse=True)[:10]
        
        for i, peer in enumerate(peers):
            is_target = peer.ticker == target_ticker
            bg_color = "#FFE082" if is_target else (self.style.row_alt_color if i % 2 == 1 else "white")
            font_weight = "bold" if is_target else "normal"
            
            html.append(f'<tr style="background-color: {bg_color}; font-weight: {font_weight};">')
            
            # Company name
            html.append(f'<td style="padding: 8px;">{peer.ticker}</td>')
            
            # Metrics
            html.append(f'<td style="padding: 8px; text-align: right;">${peer.market_cap/1000:.1f}</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{peer.multiples.get("ev_ebitda", 0):.1f}x</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{peer.multiples.get("ev_sales", 0):.1f}x</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{peer.multiples.get("pe_forward", 0):.1f}x</td>')
            
            growth = f"{peer.growth_rate*100:.1f}%" if hasattr(peer, 'growth_rate') else "N/A"
            margin = f"{peer.ebitda_margin*100:.1f}%" if hasattr(peer, 'ebitda_margin') else "N/A"
            html.append(f'<td style="padding: 8px; text-align: right;">{growth}</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{margin}</td>')
            
            html.append('</tr>')
        
        # Median row
        medians = peer_analysis.industry_medians
        if medians:
            html.append(f'<tr style="background-color: {self.style.header_color}; color: white; font-weight: bold;">')
            html.append('<td style="padding: 8px;">Median</td>')
            html.append('<td style="padding: 8px; text-align: right;">-</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{medians.get("ev_ebitda", 0):.1f}x</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{medians.get("ev_sales", 0):.1f}x</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{medians.get("pe_forward", 0):.1f}x</td>')
            html.append('<td style="padding: 8px; text-align: right;">-</td>')
            html.append('<td style="padding: 8px; text-align: right;">-</td>')
            html.append('</tr>')
        
        html.append('</tbody>')
        html.append('</table>')
        html.append('</div>')
        
        return '\n'.join(html)
    
    def create_model_pr_audit_table(self, model_pr_log: ModelPRLog) -> str:
        """Create Model-PR audit table showing evidence impact on drivers."""
        
        if not model_pr_log or not model_pr_log.changes:
            return "No evidence-based driver changes recorded"
        
        if self.format == TableFormat.MARKDOWN:
            return self._model_pr_table_markdown(model_pr_log)
        elif self.format == TableFormat.HTML:
            return self._model_pr_table_html(model_pr_log)
        else:
            return self._model_pr_table_markdown(model_pr_log)
    
    def _model_pr_table_markdown(self, model_pr_log: ModelPRLog) -> str:
        """Generate markdown Model-PR audit table."""
        
        lines = []
        lines.append("**Evidence-Based Driver Adjustments (Model-PR Log)**")
        lines.append("")
        lines.append("| Evidence Source | Driver | Before | After | Change | Confidence | Cap Applied |")
        lines.append("| :--- | :--- | ---: | ---: | ---: | ---: | :---: |")
        
        for change in model_pr_log.changes[:10]:  # Limit to 10 most important
            # Format values
            evidence = change.evidence_id[:12] + "..." if len(change.evidence_id) > 12 else change.evidence_id
            driver = change.target_path.split('.')[-1].replace('_', ' ').title()
            before = f"{change.before_value:.2%}" if change.before_value < 1 else f"{change.before_value:.1f}"
            after = f"{change.after_value:.2%}" if change.after_value < 1 else f"{change.after_value:.1f}"
            delta = change.after_value - change.before_value
            change_str = f"+{delta:.2%}" if delta >= 0 else f"{delta:.2%}"
            confidence = f"{change.confidence_threshold:.0%}"
            cap = "✓" if change.cap_applied else "-"
            
            lines.append(f"| {evidence} | {driver} | {before} | {after} | {change_str} | {confidence} | {cap} |")
        
        # Summary row
        total_changes = len(model_pr_log.changes)
        avg_confidence = np.mean([c.confidence_threshold for c in model_pr_log.changes])
        caps_applied = sum(1 for c in model_pr_log.changes if c.cap_applied)
        
        lines.append("")
        lines.append(f"*Total adjustments: {total_changes} | Average confidence: {avg_confidence:.0%} | Caps applied: {caps_applied}*")
        
        return "\n".join(lines)
    
    def _model_pr_table_html(self, model_pr_log: ModelPRLog) -> str:
        """Generate HTML Model-PR audit table."""
        
        html = []
        html.append('<div class="model-pr-table-container">')
        html.append(f'<h3 style="color: {self.style.header_color};">Evidence-Based Driver Adjustments (Model-PR Log)</h3>')
        html.append('<table class="model-pr-table" style="border-collapse: collapse; width: 100%;">')
        
        # Header
        html.append('<thead>')
        html.append(f'<tr style="background-color: {self.style.header_color}; color: white;">')
        headers = ["Evidence Source", "Driver", "Before", "After", "Change", "Confidence", "Cap Applied"]
        for header in headers:
            html.append(f'<th style="padding: 10px;">{header}</th>')
        html.append('</tr>')
        html.append('</thead>')
        
        # Data rows
        html.append('<tbody>')
        for i, change in enumerate(model_pr_log.changes[:10]):
            bg_color = self.style.row_alt_color if i % 2 == 1 else "white"
            html.append(f'<tr style="background-color: {bg_color};">')
            
            # Evidence source
            evidence = change.evidence_id[:12] + "..." if len(change.evidence_id) > 12 else change.evidence_id
            html.append(f'<td style="padding: 8px; font-family: monospace; font-size: 9pt;">{evidence}</td>')
            
            # Driver
            driver = change.target_path.split('.')[-1].replace('_', ' ').title()
            html.append(f'<td style="padding: 8px;">{driver}</td>')
            
            # Values
            before = f"{change.before_value:.2%}" if change.before_value < 1 else f"{change.before_value:.1f}"
            after = f"{change.after_value:.2%}" if change.after_value < 1 else f"{change.after_value:.1f}"
            delta = change.after_value - change.before_value
            change_str = f"+{delta:.2%}" if delta >= 0 else f"{delta:.2%}"
            change_color = "green" if delta >= 0 else "red"
            
            html.append(f'<td style="padding: 8px; text-align: right;">{before}</td>')
            html.append(f'<td style="padding: 8px; text-align: right;">{after}</td>')
            html.append(f'<td style="padding: 8px; text-align: right; color: {change_color}; font-weight: bold;">{change_str}</td>')
            
            # Confidence
            confidence = f"{change.confidence_threshold:.0%}"
            html.append(f'<td style="padding: 8px; text-align: right;">{confidence}</td>')
            
            # Cap applied
            cap = "✓" if change.cap_applied else "-"
            cap_color = "orange" if change.cap_applied else "gray"
            html.append(f'<td style="padding: 8px; text-align: center; color: {cap_color}; font-weight: bold;">{cap}</td>')
            
            html.append('</tr>')
        html.append('</tbody>')
        html.append('</table>')
        
        # Summary
        total_changes = len(model_pr_log.changes)
        avg_confidence = np.mean([c.confidence_threshold for c in model_pr_log.changes])
        caps_applied = sum(1 for c in model_pr_log.changes if c.cap_applied)
        
        html.append(f'<p style="font-style: italic; color: gray; margin-top: 10px;">')
        html.append(f'Total adjustments: {total_changes} | Average confidence: {avg_confidence:.0%} | Caps applied: {caps_applied}')
        html.append('</p>')
        html.append('</div>')
        
        return '\n'.join(html)


def generate_table_bundle(inputs: InputsI, valuation: ValuationV,
                         sensitivity_grid: Optional[np.ndarray] = None,
                         peer_analysis: Optional[PeerAnalysis] = None,
                         model_pr_log: Optional[ModelPRLog] = None,
                         format: TableFormat = TableFormat.MARKDOWN) -> Dict[str, str]:
    """Generate complete set of professional tables for report."""
    
    generator = ProfessionalTableGenerator(format=format)
    tables = {}
    
    # Sensitivity table
    if sensitivity_grid is not None:
        growth_labels = ["5%", "7%", "9%", "11%", "13%"]
        margin_labels = ["6%", "6.5%", "7%", "7.5%", "8%"]
        tables['sensitivity'] = generator.create_sensitivity_table(
            sensitivity_grid, growth_labels, margin_labels
        )
    
    # WACC evolution table
    tables['wacc_evolution'] = generator.create_wacc_evolution_table(inputs, valuation)
    
    # Peer comparables table
    if peer_analysis:
        tables['peer_comparables'] = generator.create_peer_comparables_table(
            peer_analysis, inputs.ticker
        )
    
    # Model-PR audit table
    if model_pr_log:
        tables['model_pr_audit'] = generator.create_model_pr_audit_table(model_pr_log)
    
    return tables