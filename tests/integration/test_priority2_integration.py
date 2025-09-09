#!/usr/bin/env python3
"""
Priority 2 Integration Tests

Comprehensive test suite for DBOT Quality Gap Priority 2 implementation:
- Professional narrative generation with evidence citations
- Enhanced critic validation rules
- Quality metrics and citation discipline
- End-to-end integration of all Priority 2 components
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any

from investing_agent.schemas.inputs import InputsI, Drivers, Discounting, Macro, Provenance
from investing_agent.schemas.valuation import ValuationV
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
from investing_agent.kernels.ginzu import value as kernel_value
from investing_agent.agents.writer_llm_professional import create_professional_llm_writer
from investing_agent.agents.critic import check_report
from investing_agent.agents.writer_validation import WriterValidator


@pytest.fixture
def test_inputs() -> InputsI:
    """Create test inputs for Priority 2 testing."""
    drivers = Drivers(
        sales_growth=[0.10, 0.08, 0.06],
        oper_margin=[0.12, 0.13, 0.14],
        tax_rate=0.25,
        s2c_ratio=[2.0, 2.1, 2.2],
        stable_growth=0.03
    )
    
    macro = Macro(
        risk_free_curve=[0.03, 0.035, 0.04],
        erp=0.05,
        country_risk=0.0
    )
    
    discounting = Discounting(mode="end")
    
    provenance = Provenance(
        vendor="SEC EDGAR",
        source_url="https://example.com/test-10k",
        content_sha256="test1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        retrieved_at="2024-01-15T10:00:00Z"
    )
    
    return InputsI(
        company="TestCorp",
        ticker="TEST",
        revenue=[1000, 1100, 1200],
        drivers=drivers,
        wacc=[0.10, 0.10, 0.10],
        sales_to_capital=[2.0, 2.1, 2.2],
        tax_rate=0.25,
        discounting=discounting,
        macro=macro,
        provenance=provenance,
        shares_out=100,
        net_debt=50,
        cash_nonop=25
    )


@pytest.fixture
def test_valuation(test_inputs) -> ValuationV:
    """Generate test valuation from inputs."""
    return kernel_value(test_inputs)


@pytest.fixture
def test_evidence() -> EvidenceBundle:
    """Create test evidence bundle with high-confidence claims."""
    growth_claim = EvidenceClaim(
        driver="growth",
        statement="Strong market expansion opportunity",
        direction="+",
        magnitude_units="%",
        magnitude_value=2.0,
        horizon="y1",
        confidence=0.85,
        quote="Market research shows 20% growth potential"
    )
    
    margin_claim = EvidenceClaim(
        driver="margin",
        statement="Operational efficiency improvements",
        direction="+",
        magnitude_units="bps",
        magnitude_value=100,
        horizon="y2-3",
        confidence=0.80,
        quote="Cost reduction program targeting $10M savings"
    )
    
    evidence1 = EvidenceItem(
        id="ev_test_growth_001",
        source_url="https://example.com/growth-analysis",
        snapshot_id="snap_growth_test",
        source_type="news",
        title="Market Growth Analysis",
        claims=[growth_claim]
    )
    
    evidence2 = EvidenceItem(
        id="ev_test_margin_002",
        source_url="https://example.com/efficiency-study",
        snapshot_id="snap_efficiency_test",
        source_type="10K",
        title="Efficiency Program Details",
        claims=[margin_claim]
    )
    
    return EvidenceBundle(
        ticker="TEST",
        research_timestamp="2024-01-15T10:00:00Z",
        items=[evidence1, evidence2]
    )


class TestPriority2Components:
    """Test individual Priority 2 components."""
    
    def test_prompt_engineering_system(self, test_inputs, test_valuation, test_evidence):
        """Test prompt engineering system initialization and context preparation."""
        professional_writer = create_professional_llm_writer(
            inputs=test_inputs,
            valuation=test_valuation,
            evidence_bundle=test_evidence,
            prompts_dir=Path("prompts/writer")
        )
        
        # Validate prompt system
        validation = professional_writer.prompt_manager.validate_prompt_readiness()
        
        assert validation["ready"], f"Prompt system not ready: {validation['issues']}"
        assert validation["templates_loaded"] == 6, f"Expected 6 templates, got {validation['templates_loaded']}"
        assert validation["context_available"], "Context not available"
        
        # Test context preparation
        context = professional_writer.context
        assert context.company_name == "TestCorp"
        assert context.ticker == "TEST"
        assert context.value_per_share != 0, f"Value per share should be calculated: {context.value_per_share}"
    
    def test_professional_section_generation(self, test_inputs, test_valuation, test_evidence):
        """Test professional narrative section generation."""
        professional_writer = create_professional_llm_writer(
            inputs=test_inputs,
            valuation=test_valuation,
            evidence_bundle=test_evidence
        )
        
        # Generate all required sections
        section_types = [
            "Industry Context & Market Dynamics",
            "Strategic Positioning Analysis",
            "Financial Performance Review",
            "Forward-Looking Strategic Outlook",
            "Investment Thesis Development",
            "Risk Factor Analysis"
        ]
        
        professional_output = professional_writer.generate_professional_sections(section_types)
        
        assert len(professional_output.sections) == 6, f"Expected 6 sections, got {len(professional_output.sections)}"
        assert professional_output.executive_summary, "Executive summary not generated"
        assert len(professional_output.executive_summary) > 100, "Executive summary too short"
        
        # Validate each section structure
        for section in professional_output.sections:
            assert section.title, f"Section title missing for {section.section_type}"
            assert len(section.paragraphs) > 0, f"No paragraphs for {section.section_type}"
            assert len(section.key_insights) > 0, f"No key insights for {section.section_type}"
    
    def test_writer_validation_system(self, test_inputs, test_valuation):
        """Test writer validation system prevents number hallucination."""
        validator = WriterValidator(
            inputs=test_inputs,
            valuation=test_valuation,
            require_evidence_citations=True
        )
        
        # Test content with novel numbers (should fail)
        bad_content = "TestCorp achieved 45% revenue growth and 25% margin expansion."
        validation_errors = validator.validate_numeric_content(bad_content)
        
        assert len(validation_errors) > 0, "Should detect novel numbers"
        # Check that some novel numbers are detected (exact format may vary)
        error_text = " ".join(validation_errors)
        assert "45" in error_text or "25" in error_text, f"Should detect novel numbers in: {validation_errors}"
        
        # Test content with allowed numbers (should pass)
        good_content = f"TestCorp value per share is {test_valuation.value_per_share:.2f} [ref:computed:valuation.value_per_share]."
        validation_errors = validator.validate_numeric_content(good_content)
        
        assert len(validation_errors) == 0, f"Should not flag allowed numbers: {validation_errors}"
    
    def test_enhanced_critic_validation(self, test_inputs, test_valuation, test_evidence):
        """Test enhanced critic validation rules."""
        
        # Create test report with various issues
        test_report = f"""# TestCorp Investment Analysis

## Summary
- Value per share: {test_valuation.value_per_share:.2f}
- Equity value: {test_valuation.equity_value:,.0f}
- PV (explicit): {test_valuation.pv_explicit:,.0f}
- PV (terminal): {test_valuation.pv_terminal:,.0f}
- Shares out: {test_valuation.shares_out:,.0f}

## Strategic Positioning Analysis
TestCorp demonstrates strong competitive advantages in the market. The company maintains significant market leadership through superior execution. These factors provide sustainable growth opportunities.

TestCorp achieved 15% revenue growth [ev_test_growth_001] and expanded margins to 18% [ev_test_margin_002]. However, the company also faces challenges with 35% market volatility affecting performance.

The company is well-positioned in the industry and benefits from market trends.

## Per-Year Detail
| Year | Revenue |
|------|---------|
| 2024 | 1100    |

## Terminal Value
- Next-year FCFF: 150
- PV(TV): {test_valuation.pv_terminal:,.0f}

## Citations
- Test source
"""
        
        # Run enhanced critic validation
        critic_issues = check_report(
            test_report,
            test_inputs,
            test_valuation,
            evidence_bundle=test_evidence
        )
        
        # Should detect various issue types
        issue_types = {}
        for issue in critic_issues:
            if "Uncited strategic claim" in issue:
                issue_types["uncited"] = issue_types.get("uncited", 0) + 1
            elif "Novel number" in issue:
                issue_types["novel"] = issue_types.get("novel", 0) + 1
            elif "Generic assertion" in issue:
                issue_types["generic"] = issue_types.get("generic", 0) + 1
        
        assert issue_types.get("uncited", 0) > 0, "Should detect uncited claims"
        assert issue_types.get("novel", 0) > 0, "Should detect novel numbers (15%, 18%, 35%)"
        assert issue_types.get("generic", 0) > 0, "Should detect generic assertions"


class TestPriority2Integration:
    """Test end-to-end Priority 2 integration."""
    
    def test_complete_pipeline_integration(self, test_inputs, test_valuation, test_evidence):
        """Test complete Priority 2 pipeline from inputs to validated output."""
        
        # Step 1: Initialize professional writer
        professional_writer = create_professional_llm_writer(
            inputs=test_inputs,
            valuation=test_valuation,
            evidence_bundle=test_evidence
        )
        
        # Validate system readiness
        validation = professional_writer.prompt_manager.validate_prompt_readiness()
        assert validation["ready"], "System should be ready"
        
        # Step 2: Generate professional sections
        section_types = [
            "Industry Context & Market Dynamics",
            "Strategic Positioning Analysis", 
            "Financial Performance Review",
            "Forward-Looking Strategic Outlook",
            "Investment Thesis Development",
            "Risk Factor Analysis"
        ]
        
        professional_output = professional_writer.generate_professional_sections(section_types)
        assert len(professional_output.sections) == 6, "Should generate all 6 sections"
        
        # Step 3: Convert to standard pipeline format
        writer_llm_output = professional_writer.generate_writer_llm_output(section_types)
        assert len(writer_llm_output.sections) == 6, "Should convert all sections"
        
        # Step 4: Quality validation
        quality_results = professional_writer.validate_output_quality(writer_llm_output)
        assert "validation_errors" in quality_results, "Should include validation results"
        assert "quality_metrics" in quality_results, "Should include quality metrics"
        
        # The pipeline should complete successfully even if quality metrics are low
        # (since we're using simulated responses rather than real LLM calls)
        assert quality_results is not None, "Quality validation should complete"
    
    def test_priority2_success_criteria(self, test_inputs, test_valuation, test_evidence):
        """Test Priority 2 success criteria assessment."""
        
        professional_writer = create_professional_llm_writer(
            inputs=test_inputs,
            valuation=test_valuation,
            evidence_bundle=test_evidence
        )
        
        # Generate sections
        section_types = [
            "Industry Context & Market Dynamics",
            "Strategic Positioning Analysis",
            "Financial Performance Review", 
            "Forward-Looking Strategic Outlook",
            "Investment Thesis Development",
            "Risk Factor Analysis"
        ]
        
        professional_output = professional_writer.generate_professional_sections(section_types)
        
        # Test success criteria
        success_criteria = {}
        
        # Rich narrative sections matching BYD report depth
        success_criteria["rich_narrative"] = len(professional_output.sections) == 6
        assert success_criteria["rich_narrative"], "Should generate rich narrative sections"
        
        # All sections have content
        for section in professional_output.sections:
            assert len(section.paragraphs) > 0, f"Section {section.section_type} should have content"
            assert len(section.key_insights) > 0, f"Section {section.section_type} should have insights"
        
        # Executive summary generated
        assert professional_output.executive_summary, "Should generate executive summary"
        assert len(professional_output.executive_summary) > 200, "Executive summary should be substantial"
        
        # Evidence citations present in content
        full_content = professional_output.executive_summary or ""
        for section in professional_output.sections:
            for para in section.paragraphs:
                full_content += para.content
        
        # Should contain evidence citation patterns
        assert "[ev:" in full_content, "Should contain evidence citations"
        assert "[ref:computed:" in full_content, "Should contain computed references"


def test_priority2_system_integration():
    """Integration test demonstrating full Priority 2 system."""
    
    # This test validates that all Priority 2 components work together
    # without requiring external dependencies or LLM calls
    
    # Create test data
    drivers = Drivers(
        sales_growth=[0.08, 0.07, 0.06],
        oper_margin=[0.14, 0.15, 0.16], 
        tax_rate=0.25,
        s2c_ratio=[2.1, 2.1, 2.2],
        stable_growth=0.03
    )
    
    inputs = InputsI(
        company="IntegrationTest Corp",
        ticker="ITEST",
        revenue=[2000, 2160, 2311],
        drivers=drivers,
        wacc=[0.09, 0.09, 0.09],
        sales_to_capital=[2.1, 2.1, 2.2],
        tax_rate=0.25,
        discounting=Discounting(mode="end"),
        macro=Macro(risk_free_curve=[0.03, 0.035, 0.04], erp=0.05, country_risk=0.0),
        provenance=Provenance(
            vendor="SEC EDGAR",
            source_url="https://example.com/integration-test",
            content_sha256="integration" + "1234567890abcdef" * 3,  # 64 chars
            retrieved_at="2024-01-15T10:00:00Z"
        ),
        shares_out=150,
        net_debt=100,
        cash_nonop=50
    )
    
    valuation = kernel_value(inputs)
    
    # Create evidence bundle
    evidence = EvidenceBundle(
        ticker="ITEST",
        research_timestamp="2024-01-15T10:00:00Z",
        items=[
            EvidenceItem(
                id="ev_integration_001",
                source_url="https://example.com/test-source",
                snapshot_id="snap_integration",
                source_type="news",
                title="Integration Test Evidence",
                claims=[
                    EvidenceClaim(
                        driver="growth",
                        statement="Integration test growth driver",
                        direction="+",
                        magnitude_units="%",
                        magnitude_value=1.5,
                        horizon="y1", 
                        confidence=0.83,
                        quote="Integration test shows positive growth"
                    )
                ]
            )
        ]
    )
    
    # Test complete integration
    professional_writer = create_professional_llm_writer(
        inputs=inputs,
        valuation=valuation,
        evidence_bundle=evidence
    )
    
    # System should be ready
    validation = professional_writer.prompt_manager.validate_prompt_readiness()
    assert validation["ready"], "Integration system should be ready"
    
    # Generate all sections
    all_sections = [
        "Industry Context & Market Dynamics",
        "Strategic Positioning Analysis",
        "Financial Performance Review",
        "Forward-Looking Strategic Outlook", 
        "Investment Thesis Development",
        "Risk Factor Analysis"
    ]
    
    professional_output = professional_writer.generate_professional_sections(all_sections)
    
    # Validate complete output
    assert len(professional_output.sections) == 6, "Should generate all required sections"
    assert professional_output.executive_summary, "Should generate executive summary"
    
    # Convert to standard format
    writer_llm_output = professional_writer.generate_writer_llm_output(all_sections)
    assert len(writer_llm_output.sections) == 6, "Should convert all sections"
    
    print("✅ Priority 2 integration test completed successfully")
    print(f"   - Generated {len(professional_output.sections)} professional sections")
    print(f"   - Executive summary: {len(professional_output.executive_summary)} characters")  
    print(f"   - System integration: All components working")


if __name__ == "__main__":
    # Run integration test directly
    test_priority2_system_integration()