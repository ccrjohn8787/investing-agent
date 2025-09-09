"""Professional report assembly engine for investment reports."""

from __future__ import annotations

import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle
from investing_agent.schemas.comparables import PeerAnalysis
from investing_agent.schemas.model_pr_log import ModelPRLog
from investing_agent.schemas.report_structure import ReportStructure, SectionType
from investing_agent.agents.section_orchestrator import SectionOrchestrator, SectionContent
from investing_agent.agents.visualization_professional import ProfessionalVisualizer, generate_chart_bundle
from investing_agent.agents.table_generator import ProfessionalTableGenerator, generate_table_bundle, TableFormat
from investing_agent.agents.sensitivity import compute_sensitivity


logger = logging.getLogger(__name__)


class ProfessionalReportAssembler:
    """Assemble professional investment reports from all components."""
    
    def __init__(self, format: str = "markdown"):
        self.format = format
        self.orchestrator = SectionOrchestrator()
        self.visualizer = ProfessionalVisualizer()
        self.table_generator = ProfessionalTableGenerator(
            format=TableFormat.MARKDOWN if format == "markdown" else TableFormat.HTML
        )
        
    def assemble_report(self,
                       inputs: InputsI,
                       valuation: ValuationV,
                       evidence: Optional[EvidenceBundle] = None,
                       peer_analysis: Optional[PeerAnalysis] = None,
                       model_pr_log: Optional[ModelPRLog] = None,
                       llm_sections: Optional[Dict[str, str]] = None) -> str:
        """Assemble complete professional report."""
        
        logger.info(f"Assembling professional report for {inputs.ticker}")
        
        # Generate all visualizations
        charts = self._generate_charts(inputs, valuation, peer_analysis)
        
        # Generate all tables
        tables = self._generate_tables(inputs, valuation, peer_analysis, model_pr_log)
        
        # Get report structure
        report_structure = self.orchestrator.orchestrate_report(
            inputs, valuation, evidence, peer_analysis, charts, tables
        )
        
        # Generate section content
        sections = []
        for section_def in report_structure.sections:
            content = self.orchestrator.generate_section_content(
                section_def, inputs, valuation, evidence, peer_analysis, charts, tables
            )
            
            # Integrate LLM-generated content if available
            if llm_sections and section_def.section_type.value in llm_sections:
                content.narrative = llm_sections[section_def.section_type.value]
            
            sections.append(content)
        
        # Assemble final report
        report = self._assemble_markdown_report(report_structure, sections)
        
        logger.info(f"Report assembly complete: {len(sections)} sections, {len(report)} characters")
        
        return report
    
    def _generate_charts(self, inputs: InputsI, valuation: ValuationV,
                        peer_analysis: Optional[PeerAnalysis]) -> Dict[str, bytes]:
        """Generate all charts for the report."""
        
        charts = {}
        
        try:
            # Generate chart bundle
            chart_bundle = generate_chart_bundle(inputs, valuation, peer_analysis)
            charts.update(chart_bundle)
            
            # Generate sensitivity heatmap
            sensitivity = compute_sensitivity(inputs)
            if sensitivity:
                growth_labels = [f"{(g-0.02)*100:.0f}%" for g in [0.03, 0.05, 0.07, 0.09, 0.11]]
                margin_labels = [f"{m*100:.1f}%" for m in [0.06, 0.065, 0.07, 0.075, 0.08]]
                charts['sensitivity_heatmap'] = self.visualizer.create_sensitivity_heatmap_professional(
                    sensitivity.grid, growth_labels, margin_labels, valuation.value_per_share
                )
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
        
        logger.info(f"Generated {len(charts)} charts")
        return charts
    
    def _generate_tables(self, inputs: InputsI, valuation: ValuationV,
                        peer_analysis: Optional[PeerAnalysis],
                        model_pr_log: Optional[ModelPRLog]) -> Dict[str, str]:
        """Generate all tables for the report."""
        
        tables = {}
        
        try:
            # Generate sensitivity grid
            sensitivity = compute_sensitivity(inputs)
            sensitivity_grid = sensitivity.grid if sensitivity else None
            
            # Generate table bundle
            table_bundle = generate_table_bundle(
                inputs, valuation, sensitivity_grid, peer_analysis, model_pr_log
            )
            tables.update(table_bundle)
            
            # Add valuation summary table
            tables['valuation_summary'] = self._create_valuation_summary_table(inputs, valuation)
            
            # Add financial projections table
            tables['financial_projections'] = self._create_financial_projections_table(inputs, valuation)
            
        except Exception as e:
            logger.error(f"Error generating tables: {e}")
        
        logger.info(f"Generated {len(tables)} tables")
        return tables
    
    def _create_valuation_summary_table(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Create valuation summary table."""
        
        lines = []
        lines.append("**Valuation Summary**")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("| :--- | ---: |")
        lines.append(f"| Enterprise Value | ${valuation.enterprise_value:,.0f}M |")
        lines.append(f"| Less: Net Debt | $({inputs.net_debt:,.0f}M) |")
        lines.append(f"| Equity Value | ${valuation.enterprise_value - inputs.net_debt:,.0f}M |")
        lines.append(f"| Shares Outstanding | {inputs.shares_outstanding:,.0f}M |")
        lines.append(f"| **Value per Share** | **${valuation.value_per_share:.2f}** |")
        lines.append(f"| Current Price | $[MARKET_PRICE] |")
        lines.append(f"| **Upside/(Downside)** | **[X]%** |")
        
        return "\n".join(lines)
    
    def _create_financial_projections_table(self, inputs: InputsI, valuation: ValuationV) -> str:
        """Create financial projections table."""
        
        lines = []
        lines.append("**Financial Projections**")
        lines.append("")
        lines.append("| Year | Revenue ($M) | Growth | EBITDA ($M) | Margin | FCF ($M) |")
        lines.append("| :--- | ---: | ---: | ---: | ---: | ---: |")
        
        # Generate projections for first 5 years
        for i in range(min(5, inputs.horizon)):
            year = datetime.now().year + i + 1
            revenue = valuation.revenue_projection[i] if i < len(valuation.revenue_projection) else 0
            growth = inputs.drivers.sales_growth[i] * 100 if i < len(inputs.drivers.sales_growth) else 0
            ebitda = valuation.ebitda_projection[i] if i < len(valuation.ebitda_projection) else 0
            margin = (ebitda / revenue * 100) if revenue > 0 else 0
            fcf = ebitda * 0.7  # Simplified FCF calculation
            
            lines.append(f"| {year} | ${revenue:,.0f} | {growth:.1f}% | ${ebitda:,.0f} | {margin:.1f}% | ${fcf:,.0f} |")
        
        return "\n".join(lines)
    
    def _assemble_markdown_report(self, structure: ReportStructure, sections: List[SectionContent]) -> str:
        """Assemble final markdown report."""
        
        lines = []
        
        # Title and header
        lines.append(f"# {structure.report_title}")
        if structure.report_subtitle:
            lines.append(f"## {structure.report_subtitle}")
        lines.append("")
        
        # Report metadata
        lines.append(f"**Company:** {structure.company} ({structure.ticker})")
        lines.append(f"**Date:** {structure.report_date}")
        lines.append(f"**Analyst:** {structure.analyst_name}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Table of contents
        if structure.include_toc:
            lines.append("## Table of Contents")
            lines.append("")
            for i, section in enumerate(sections, 1):
                lines.append(f"{i}. [{section.title}](#{section.title.lower().replace(' ', '-')})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Main content sections
        for section in sections:
            # Add section narrative
            if section.narrative:
                lines.append(section.narrative)
                lines.append("")
            
            # Add tables
            if section.tables:
                for table_name, table_content in section.tables.items():
                    lines.append(table_content)
                    lines.append("")
            
            # Add charts (as embedded images or placeholders)
            if section.charts:
                for chart_name, chart_bytes in section.charts.items():
                    lines.append(self._embed_chart(chart_name, chart_bytes))
                    lines.append("")
            
            # Section separator
            lines.append("---")
            lines.append("")
        
        # Disclaimer
        if structure.include_disclaimer:
            lines.append(self._generate_disclaimer())
        
        return "\n".join(lines)
    
    def _embed_chart(self, name: str, chart_bytes: bytes) -> str:
        """Embed chart in markdown report."""
        
        # Convert bytes to base64
        chart_b64 = base64.b64encode(chart_bytes).decode('utf-8')
        
        # Create markdown image with data URI
        return f"![{name}](data:image/png;base64,{chart_b64})"
    
    def _generate_disclaimer(self) -> str:
        """Generate report disclaimer."""
        
        return """
## Disclaimer

This report has been prepared for informational purposes only and does not constitute investment advice. 
The analysis is based on publicly available information and proprietary valuation models. Past performance 
is not indicative of future results. Investors should conduct their own due diligence before making investment decisions.

The financial projections and valuation estimates contained herein are based on numerous assumptions that may 
prove to be incorrect. Actual results may differ materially from those projected. The company's stock price may 
be affected by factors not considered in this analysis.

Generated by Investing Agent - Professional Investment Analysis System
"""


class ReportFormatter:
    """Professional formatting for investment reports."""
    
    @staticmethod
    def format_executive_summary_box(summary: str) -> str:
        """Create formatted executive summary box."""
        
        lines = []
        lines.append("```")
        lines.append("┌─────────────────────────────────────────────────────────────┐")
        lines.append("│                     EXECUTIVE SUMMARY                       │")
        lines.append("├─────────────────────────────────────────────────────────────┤")
        
        # Split summary into lines and format
        summary_lines = summary.strip().split('\n')
        for line in summary_lines:
            if len(line) <= 60:
                lines.append(f"│ {line:<60} │")
            else:
                # Word wrap long lines
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= 60:
                        current_line += word + " "
                    else:
                        lines.append(f"│ {current_line:<60} │")
                        current_line = word + " "
                if current_line:
                    lines.append(f"│ {current_line:<60} │")
        
        lines.append("└─────────────────────────────────────────────────────────────┘")
        lines.append("```")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_key_metrics_dashboard(metrics: Dict[str, Any]) -> str:
        """Create formatted key metrics dashboard."""
        
        lines = []
        lines.append("### Key Metrics Dashboard")
        lines.append("")
        lines.append("| Metric | Current | Target | Upside |")
        lines.append("| :--- | ---: | ---: | ---: |")
        
        for metric, values in metrics.items():
            current = values.get('current', 0)
            target = values.get('target', 0)
            upside = ((target / current - 1) * 100) if current > 0 else 0
            
            lines.append(f"| {metric} | ${current:.2f} | ${target:.2f} | {upside:+.1f}% |")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_investment_highlights(highlights: List[str]) -> str:
        """Format investment highlights with bullets."""
        
        lines = []
        lines.append("### Investment Highlights")
        lines.append("")
        
        for highlight in highlights:
            lines.append(f"✓ **{highlight}**")
        
        return "\n".join(lines)


def create_professional_report(inputs: InputsI,
                              valuation: ValuationV,
                              evidence: Optional[EvidenceBundle] = None,
                              peer_analysis: Optional[PeerAnalysis] = None,
                              model_pr_log: Optional[ModelPRLog] = None,
                              llm_sections: Optional[Dict[str, str]] = None) -> str:
    """Main entry point to create professional investment report."""
    
    assembler = ProfessionalReportAssembler()
    
    report = assembler.assemble_report(
        inputs=inputs,
        valuation=valuation,
        evidence=evidence,
        peer_analysis=peer_analysis,
        model_pr_log=model_pr_log,
        llm_sections=llm_sections
    )
    
    return report