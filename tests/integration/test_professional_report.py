"""Integration tests for professional report generation system."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
import numpy as np

from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
from investing_agent.schemas.comparables import PeerAnalysis, PeerCompany
from investing_agent.schemas.model_pr_log import ModelPRLog, ModelPRChange
from investing_agent.schemas.report_structure import CompanyProfile, SectionType

from investing_agent.agents.report_assembler import (
    ProfessionalReportAssembler, 
    create_professional_report,
    ReportFormatter
)
from investing_agent.agents.visualization_professional import ProfessionalVisualizer
from investing_agent.agents.table_generator import ProfessionalTableGenerator, TableFormat
from investing_agent.agents.section_orchestrator import SectionOrchestrator


@pytest.fixture
def sample_inputs():
    """Create sample inputs for testing."""
    return InputsI(
        ticker="TEST",
        company="Test Corporation",
        currency="USD",
        drivers=Drivers(
            sales_growth=[0.10, 0.08, 0.06],
            oper_margin=[0.20, 0.21, 0.22],
            tax_rate=0.21
        ),
        wacc=[0.08, 0.085, 0.09],
        horizon=3,
        revenue_base=1000.0,
        shares_outstanding=100.0,
        net_debt=200.0
    )


@pytest.fixture
def sample_valuation():
    """Create sample valuation for testing."""
    return ValuationV(
        ticker="TEST",
        value_per_share=150.0,
        enterprise_value=15000.0,
        revenue_projection=[1100.0, 1188.0, 1259.3],
        ebitda_projection=[220.0, 249.5, 277.0],
        present_value_sum=12000.0,
        terminal_value=8000.0,
        total_pv=15000.0
    )


@pytest.fixture
def sample_evidence():
    """Create sample evidence bundle for testing."""
    return EvidenceBundle(
        research_timestamp="2024-01-01T00:00:00Z",
        ticker="TEST",
        items=[
            EvidenceItem(
                id="ev_001",
                source_url="https://example.com/earnings",
                snapshot_id="snap_001",
                date="2024-01-01",
                source_type="transcript",
                title="Q4 2023 Earnings Call",
                claims=[
                    EvidenceClaim(
                        driver="growth",
                        statement="Management expects 10% revenue growth",
                        direction="+",
                        magnitude_units="%",
                        magnitude_value=10.0,
                        horizon="y1",
                        confidence=0.85,
                        quote="We expect revenue growth of approximately 10% next year"
                    )
                ]
            )
        ]
    )


@pytest.fixture
def sample_peer_analysis():
    """Create sample peer analysis for testing."""
    return PeerAnalysis(
        peer_companies=[
            PeerCompany(
                ticker="PEER1",
                company_name="Peer Company 1",
                market_cap=20000.0,
                multiples={
                    "ev_ebitda": 15.0,
                    "ev_sales": 3.0,
                    "pe_forward": 20.0
                }
            ),
            PeerCompany(
                ticker="PEER2",
                company_name="Peer Company 2",
                market_cap=18000.0,
                multiples={
                    "ev_ebitda": 14.0,
                    "ev_sales": 2.8,
                    "pe_forward": 18.0
                }
            )
        ],
        industry_medians={
            "ev_ebitda": 14.5,
            "ev_sales": 2.9,
            "pe_forward": 19.0
        }
    )


@pytest.fixture
def sample_model_pr_log():
    """Create sample Model-PR log for testing."""
    return ModelPRLog(
        ticker="TEST",
        timestamp="2024-01-01T00:00:00Z",
        changes=[
            ModelPRChange(
                evidence_id="ev_001",
                target_path="drivers.sales_growth[0]",
                before_value=0.08,
                after_value=0.10,
                change_reason="Management guidance",
                applied_rule="growth_cap_y1_500bps",
                cap_applied=False,
                confidence_threshold=0.85
            )
        ]
    )


class TestProfessionalVisualizer:
    """Test professional visualization components."""
    
    def test_peer_multiples_chart(self, sample_peer_analysis):
        """Test peer multiples chart generation."""
        visualizer = ProfessionalVisualizer()
        
        chart_bytes = visualizer.create_peer_multiples_chart(
            sample_peer_analysis, "TEST", "ev_ebitda"
        )
        
        assert chart_bytes is not None
        assert len(chart_bytes) > 0
        assert chart_bytes[:4] == b'\x89PNG'  # PNG header
    
    def test_financial_trajectory_chart(self, sample_inputs, sample_valuation):
        """Test financial trajectory chart generation."""
        visualizer = ProfessionalVisualizer()
        
        chart_bytes = visualizer.create_financial_trajectory_chart(
            sample_inputs, sample_valuation
        )
        
        assert chart_bytes is not None
        assert len(chart_bytes) > 0
    
    def test_value_bridge_waterfall(self, sample_valuation):
        """Test value bridge waterfall chart."""
        visualizer = ProfessionalVisualizer()
        
        chart_bytes = visualizer.create_value_bridge_waterfall(sample_valuation)
        
        assert chart_bytes is not None
        assert len(chart_bytes) > 0
    
    def test_sensitivity_heatmap(self):
        """Test sensitivity heatmap generation."""
        visualizer = ProfessionalVisualizer()
        
        # Create sample sensitivity grid
        grid = np.random.uniform(100, 200, (5, 5))
        growth_labels = ["5%", "7%", "9%", "11%", "13%"]
        margin_labels = ["6%", "6.5%", "7%", "7.5%", "8%"]
        
        chart_bytes = visualizer.create_sensitivity_heatmap_professional(
            grid, growth_labels, margin_labels, 150.0
        )
        
        assert chart_bytes is not None
        assert len(chart_bytes) > 0


class TestProfessionalTableGenerator:
    """Test professional table generation."""
    
    def test_sensitivity_table_markdown(self):
        """Test markdown sensitivity table generation."""
        generator = ProfessionalTableGenerator(format=TableFormat.MARKDOWN)
        
        grid = np.random.uniform(100, 200, (5, 5))
        growth_labels = ["5%", "7%", "9%", "11%", "13%"]
        margin_labels = ["6%", "6.5%", "7%", "7.5%", "8%"]
        
        table = generator.create_sensitivity_table(grid, growth_labels, margin_labels)
        
        assert table is not None
        assert "Valuation Sensitivity Analysis" in table
        assert "| Revenue Growth \\ Operating Margin |" in table
        assert all(label in table for label in growth_labels)
    
    def test_wacc_evolution_table(self, sample_inputs, sample_valuation):
        """Test WACC evolution table generation."""
        generator = ProfessionalTableGenerator(format=TableFormat.MARKDOWN)
        
        table = generator.create_wacc_evolution_table(sample_inputs, sample_valuation)
        
        assert table is not None
        assert "Cost of Capital Evolution" in table
        assert "Terminal Value" in table
        assert "WACC" in table
    
    def test_peer_comparables_table(self, sample_peer_analysis):
        """Test peer comparables table generation."""
        generator = ProfessionalTableGenerator(format=TableFormat.MARKDOWN)
        
        table = generator.create_peer_comparables_table(sample_peer_analysis, "TEST")
        
        assert table is not None
        assert "Peer Group Comparison" in table
        assert "PEER1" in table
        assert "PEER2" in table
        assert "Median" in table
    
    def test_model_pr_audit_table(self, sample_model_pr_log):
        """Test Model-PR audit table generation."""
        generator = ProfessionalTableGenerator(format=TableFormat.MARKDOWN)
        
        table = generator.create_model_pr_audit_table(sample_model_pr_log)
        
        assert table is not None
        assert "Evidence-Based Driver Adjustments" in table
        assert "ev_001" in table
        assert "Sales Growth" in table


class TestSectionOrchestrator:
    """Test section orchestration system."""
    
    def test_company_profile_detection(self, sample_inputs):
        """Test company profile determination."""
        from investing_agent.schemas.report_structure import get_company_profile
        
        profile = get_company_profile(sample_inputs)
        
        assert profile in CompanyProfile
    
    def test_section_selection(self, sample_inputs, sample_evidence, sample_peer_analysis):
        """Test dynamic section selection."""
        from investing_agent.schemas.report_structure import select_sections_for_company
        
        available_data = {
            "peer_analysis": True,
            "evidence_data": True,
            "sensitivity_data": True
        }
        
        sections = select_sections_for_company(CompanyProfile.HIGH_GROWTH, available_data)
        
        assert len(sections) > 0
        assert any(s.section_type == SectionType.EXECUTIVE_SUMMARY for s in sections)
        assert any(s.section_type == SectionType.INVESTMENT_THESIS for s in sections)
    
    def test_section_content_generation(self, sample_inputs, sample_valuation):
        """Test section content generation."""
        orchestrator = SectionOrchestrator()
        
        from investing_agent.schemas.report_structure import get_standard_sections
        section_def = get_standard_sections()[SectionType.EXECUTIVE_SUMMARY]
        
        content = orchestrator.generate_section_content(
            section_def, sample_inputs, sample_valuation
        )
        
        assert content is not None
        assert content.section_type == SectionType.EXECUTIVE_SUMMARY
        assert content.title == "Executive Summary"
        assert content.narrative is not None
        assert content.word_count > 0


class TestReportAssembler:
    """Test report assembly system."""
    
    def test_report_assembly(self, sample_inputs, sample_valuation, 
                            sample_evidence, sample_peer_analysis, sample_model_pr_log):
        """Test complete report assembly."""
        assembler = ProfessionalReportAssembler()
        
        report = assembler.assemble_report(
            inputs=sample_inputs,
            valuation=sample_valuation,
            evidence=sample_evidence,
            peer_analysis=sample_peer_analysis,
            model_pr_log=sample_model_pr_log
        )
        
        assert report is not None
        assert len(report) > 0
        assert sample_inputs.company in report
        assert sample_inputs.ticker in report
        assert "Executive Summary" in report
    
    def test_chart_generation(self, sample_inputs, sample_valuation, sample_peer_analysis):
        """Test chart generation in assembler."""
        assembler = ProfessionalReportAssembler()
        
        charts = assembler._generate_charts(sample_inputs, sample_valuation, sample_peer_analysis)
        
        assert charts is not None
        assert len(charts) > 0
        assert all(isinstance(v, bytes) for v in charts.values())
    
    def test_table_generation(self, sample_inputs, sample_valuation, 
                            sample_peer_analysis, sample_model_pr_log):
        """Test table generation in assembler."""
        assembler = ProfessionalReportAssembler()
        
        tables = assembler._generate_tables(
            sample_inputs, sample_valuation, sample_peer_analysis, sample_model_pr_log
        )
        
        assert tables is not None
        assert len(tables) > 0
        assert all(isinstance(v, str) for v in tables.values())
    
    def test_markdown_assembly(self, sample_inputs, sample_valuation):
        """Test markdown report assembly."""
        from investing_agent.schemas.report_structure import ReportStructure, ReportSection
        from investing_agent.agents.section_orchestrator import SectionContent
        
        assembler = ProfessionalReportAssembler()
        
        structure = ReportStructure(
            report_title="Test Report",
            company="TEST",
            ticker="TEST",
            report_date="2024-01-01",
            sections=[]
        )
        
        sections = [
            SectionContent(
                section_type=SectionType.EXECUTIVE_SUMMARY,
                title="Executive Summary",
                narrative="Test summary content",
                word_count=10
            )
        ]
        
        report = assembler._assemble_markdown_report(structure, sections)
        
        assert report is not None
        assert "Test Report" in report
        assert "Executive Summary" in report
        assert "Test summary content" in report


class TestReportFormatter:
    """Test report formatting utilities."""
    
    def test_executive_summary_box(self):
        """Test executive summary box formatting."""
        summary = "This is a test summary with important information."
        
        formatted = ReportFormatter.format_executive_summary_box(summary)
        
        assert formatted is not None
        assert "EXECUTIVE SUMMARY" in formatted
        assert "test summary" in formatted
        assert "┌" in formatted and "└" in formatted
    
    def test_key_metrics_dashboard(self):
        """Test key metrics dashboard formatting."""
        metrics = {
            "Stock Price": {"current": 100, "target": 150},
            "EV/EBITDA": {"current": 12, "target": 10},
            "Revenue": {"current": 1000, "target": 1500}
        }
        
        dashboard = ReportFormatter.format_key_metrics_dashboard(metrics)
        
        assert dashboard is not None
        assert "Key Metrics Dashboard" in dashboard
        assert "Stock Price" in dashboard
        assert "+50.0%" in dashboard
    
    def test_investment_highlights(self):
        """Test investment highlights formatting."""
        highlights = [
            "Strong market position",
            "Growing margins",
            "Excellent management team"
        ]
        
        formatted = ReportFormatter.format_investment_highlights(highlights)
        
        assert formatted is not None
        assert "Investment Highlights" in formatted
        assert all(h in formatted for h in highlights)
        assert "✓" in formatted


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_create_professional_report(self, sample_inputs, sample_valuation,
                                       sample_evidence, sample_peer_analysis,
                                       sample_model_pr_log):
        """Test main report creation function."""
        
        report = create_professional_report(
            inputs=sample_inputs,
            valuation=sample_valuation,
            evidence=sample_evidence,
            peer_analysis=sample_peer_analysis,
            model_pr_log=sample_model_pr_log
        )
        
        assert report is not None
        assert len(report) > 1000  # Should be substantial
        assert "Test Corporation" in report
        assert "Investment" in report
        assert "Valuation" in report
    
    def test_report_with_llm_sections(self, sample_inputs, sample_valuation):
        """Test report with LLM-generated sections."""
        
        llm_sections = {
            "executive_summary": "This is an LLM-generated executive summary.",
            "investment_thesis": "This is an LLM-generated investment thesis."
        }
        
        report = create_professional_report(
            inputs=sample_inputs,
            valuation=sample_valuation,
            llm_sections=llm_sections
        )
        
        assert report is not None
        # Note: LLM sections would be integrated if section types match
    
    def test_report_output_to_file(self, sample_inputs, sample_valuation):
        """Test saving report to file."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            report = create_professional_report(
                inputs=sample_inputs,
                valuation=sample_valuation
            )
            
            output_path = Path(tmpdir) / "test_report.md"
            output_path.write_text(report)
            
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            
            # Verify content
            content = output_path.read_text()
            assert "Test Corporation" in content


if __name__ == "__main__":
    pytest.main([__file__])