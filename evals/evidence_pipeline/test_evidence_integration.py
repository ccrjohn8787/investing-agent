#!/usr/bin/env python3
"""
Evidence Pipeline Integration Tests

Comprehensive evaluation of evidence pipeline functionality including:
- Evidence generation and quality
- Driver change accuracy  
- Evidence freezing consistency
- Provenance chain integrity
"""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import json

from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
from investing_agent.orchestration.evidence_integration import EvidenceIntegrationManager
from investing_agent.orchestration.manifest import Manifest


class TestEvidencePipelineIntegration:
    """Test suite for evidence pipeline integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.ticker = "TEST"
        
        # Create test InputsI
        self.test_inputs = InputsI(
            company="Test Company",
            ticker=self.ticker,
            shares_out=100.0,
            revenue_t0=1000.0,
            drivers=Drivers(
                sales_growth=[0.10, 0.08],  # 10%, 8%
                oper_margin=[0.15, 0.16],   # 15%, 16%
                stable_growth=0.02,
                stable_margin=0.12
            ),
            sales_to_capital=[2.0, 2.1],
            wacc=[0.08, 0.09]
        )
        
        # Create test manifest
        self.manifest = Manifest(run_id="test_run", ticker=self.ticker)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_evidence_pipeline_disabled(self):
        """Test backward compatibility with evidence pipeline disabled."""
        integration_manager = EvidenceIntegrationManager(
            enable_evidence_pipeline=False,
            output_dir=self.test_dir
        )
        
        # Should return unchanged inputs
        result_inputs, evidence_artifacts = integration_manager.execute_evidence_enhanced_research(
            self.ticker, self.test_inputs, self.manifest
        )
        
        # Verify no changes
        assert result_inputs.drivers.sales_growth == self.test_inputs.drivers.sales_growth
        assert result_inputs.drivers.oper_margin == self.test_inputs.drivers.oper_margin
        
        # Verify no evidence artifacts
        assert evidence_artifacts['evidence_bundle'] is None
        assert evidence_artifacts['model_pr_log'] is None
    
    def test_mock_evidence_generation(self):
        """Test evidence generation with mock data."""
        # Create mock evidence bundle
        mock_evidence = self._create_mock_evidence_bundle()
        
        # Test evidence quality validation
        from investing_agent.orchestration.evidence_processor import validate_evidence_bundle_quality
        quality_metrics = validate_evidence_bundle_quality(mock_evidence)
        
        # Verify quality metrics
        assert quality_metrics['bundle_validation']['is_valid']
        assert quality_metrics['bundle_validation']['high_confidence_claims'] >= 2
        
        print(f"Mock evidence quality score: {quality_metrics}")
    
    def test_evidence_freezing_workflow(self):
        """Test complete evidence freezing workflow."""
        integration_manager = EvidenceIntegrationManager(output_dir=self.test_dir)
        
        # Create mock evidence
        evidence_bundle = self._create_mock_evidence_bundle()
        
        # Freeze evidence
        frozen_evidence = integration_manager.evidence_freezer.freeze_evidence_bundle(
            evidence_bundle, self.manifest, "Test freeze"
        )
        
        # Verify freeze properties
        assert frozen_evidence.frozen
        assert frozen_evidence.freeze_timestamp is not None
        assert frozen_evidence.content_hash is not None
        
        # Verify integrity
        integrity_result = integration_manager.evidence_freezer.verify_freeze_integrity(frozen_evidence)
        assert integrity_result['is_valid']
        
        print(f"Evidence frozen successfully: {frozen_evidence.freeze_timestamp}")
    
    def test_driver_change_application(self):
        """Test evidence-based driver changes."""
        integration_manager = EvidenceIntegrationManager(
            confidence_threshold=0.80,
            output_dir=self.test_dir
        )
        
        # Create evidence with specific driver claims
        evidence_bundle = self._create_targeted_evidence_bundle()
        
        # Apply evidence to inputs
        modified_inputs, pr_log, processing_summary = integration_manager.evidence_processor.ingest_evidence(
            self.test_inputs, evidence_bundle, dry_run=False
        )
        
        # Verify changes were applied
        assert pr_log.validation_summary['total_applied'] > 0
        
        # Verify specific driver modifications
        growth_changes = pr_log.get_changes_by_driver("drivers.sales_growth")
        assert len(growth_changes) > 0
        
        # Verify audit trail
        for change in growth_changes:
            assert change.evidence_id.startswith('ev_')
            assert change.confidence_threshold == 0.80
            assert change.change_magnitude > 0
        
        print(f"Applied {pr_log.validation_summary['total_applied']} driver changes")
    
    def test_provenance_chain_integrity(self):
        """Test complete provenance chain validation."""
        integration_manager = EvidenceIntegrationManager(output_dir=self.test_dir)
        
        # Create evidence with snapshots
        evidence_bundle = self._create_evidence_with_snapshots()
        
        # Extract snapshot references
        snapshot_refs = []
        for item in evidence_bundle.items:
            # Create snapshot reference for testing
            from investing_agent.schemas.evidence import SnapshotReference
            snapshot_ref = SnapshotReference(
                url=item.source_url,
                retrieved_at=datetime.now().isoformat(),
                content_sha256="a" * 64,  # Mock hash
                license_info="Test License"
            )
            snapshot_refs.append(snapshot_ref)
        
        # Create provenance chain
        provenance_chain = integration_manager.snapshot_manager.create_provenance_chain(
            snapshot_refs, self.ticker
        )
        
        # Verify chain properties
        assert provenance_chain['ticker'] == self.ticker
        assert provenance_chain['total_snapshots'] == len(snapshot_refs)
        assert len(provenance_chain['chain_links']) == len(snapshot_refs)
        
        print(f"Provenance chain created with {len(snapshot_refs)} links")
    
    def test_evidence_coverage_metrics(self):
        """Test evidence coverage evaluation."""
        # Create evidence bundle with varied coverage
        evidence_bundle = self._create_coverage_test_evidence()
        
        # Validate coverage
        from investing_agent.schemas.evidence import validate_evidence_bundle
        validation_result = validate_evidence_bundle(evidence_bundle, confidence_threshold=0.80)
        
        # Check coverage metrics
        coverage_metrics = validation_result.coverage_metrics
        
        # Verify driver coverage
        assert 'drivers_covered' in coverage_metrics
        assert len(coverage_metrics['drivers_covered']) >= 2  # At least 2 drivers
        
        # Verify confidence ratio
        assert coverage_metrics['confidence_ratio'] >= 0.70  # At least 70% high confidence
        
        print(f"Coverage metrics: {coverage_metrics}")
    
    def test_narrative_context_creation(self):
        """Test narrative context generation for writer agents."""
        integration_manager = EvidenceIntegrationManager(output_dir=self.test_dir)
        
        # Create evidence artifacts
        evidence_bundle = self._create_mock_evidence_bundle()
        evidence_artifacts = {
            'evidence_bundle': evidence_bundle,
            'model_pr_log': None,
            'processing_summary': {'quality_score': 0.85}
        }
        
        # Create narrative context
        narrative_context = integration_manager.create_narrative_evidence_context(evidence_artifacts)
        
        # Verify context structure
        assert narrative_context is not None
        assert narrative_context['evidence_available']
        assert narrative_context['total_evidence_items'] > 0
        assert 'citations_available' in narrative_context
        assert 'access_token' in narrative_context
        
        # Verify backward compatibility
        assert 'insights_bundle' in narrative_context
        
        print(f"Narrative context created with {len(narrative_context['citations_available'])} citations")
    
    def test_integration_validation(self):
        """Test integration validation functionality."""
        integration_manager = EvidenceIntegrationManager(output_dir=self.test_dir)
        
        # Validate integration
        validation_results = integration_manager.validate_pipeline_integration(self.ticker)
        
        # Verify validation structure
        assert validation_results['ticker'] == self.ticker
        assert validation_results['pipeline_enabled']
        assert 'components_available' in validation_results
        assert 'integration_status' in validation_results
        
        # Verify component availability
        components = validation_results['components_available']
        assert components['research_agent'] is True
        assert components['evidence_processor'] is True
        
        print(f"Integration validation: {validation_results['integration_status']}")
    
    def _create_mock_evidence_bundle(self) -> EvidenceBundle:
        """Create mock evidence bundle for testing."""
        # Create mock claims
        growth_claim = EvidenceClaim(
            driver="growth",
            statement="Management raised growth guidance to 12-15%",
            direction="+",
            magnitude_units="%",
            magnitude_value=3.0,  # 3% increase
            horizon="y1",
            confidence=0.85,
            quote="We now expect revenue growth of 12-15% in 2025"
        )
        
        margin_claim = EvidenceClaim(
            driver="margin",
            statement="Cost optimization program expected to improve margins",
            direction="+",
            magnitude_units="bps",
            magnitude_value=150.0,  # 150bps increase
            horizon="y2-3",
            confidence=0.82,
            quote="Our cost optimization initiatives should improve operating margins by 150 basis points"
        )
        
        # Create evidence item
        evidence_item = EvidenceItem(
            id="ev_test001",
            source_url="https://example.com/earnings-call",
            snapshot_id="snap_test001",
            date="2025-01-15",
            source_type="transcript",
            title="Q4 2024 Earnings Call",
            claims=[growth_claim, margin_claim]
        )
        
        # Create evidence bundle
        evidence_bundle = EvidenceBundle(
            research_timestamp=datetime.now().isoformat(),
            ticker=self.ticker,
            items=[evidence_item]
        )
        
        return evidence_bundle
    
    def _create_targeted_evidence_bundle(self) -> EvidenceBundle:
        """Create evidence bundle with specific driver targets."""
        claims = []
        
        # Growth claim targeting y1
        claims.append(EvidenceClaim(
            driver="growth",
            statement="Revenue guidance raised to 15%",
            direction="+",
            magnitude_units="%",
            magnitude_value=5.0,  # 5% increase (should be capped to 5%)
            horizon="y1",
            confidence=0.90,
            quote="Revenue growth expected to reach 15%"
        ))
        
        # Margin claim targeting y1
        claims.append(EvidenceClaim(
            driver="margin",
            statement="Margin improvement from efficiency gains",
            direction="+",
            magnitude_units="bps",
            magnitude_value=100.0,  # 100bps increase
            horizon="y1",
            confidence=0.88,
            quote="Operating margins should improve by approximately 100 basis points"
        ))
        
        evidence_item = EvidenceItem(
            id="ev_targeted",
            source_url="https://example.com/guidance-update",
            snapshot_id="snap_targeted",
            date="2025-01-20",
            source_type="PR",
            title="Guidance Update",
            claims=claims
        )
        
        return EvidenceBundle(
            research_timestamp=datetime.now().isoformat(),
            ticker=self.ticker,
            items=[evidence_item]
        )
    
    def _create_evidence_with_snapshots(self) -> EvidenceBundle:
        """Create evidence bundle with snapshot references."""
        # Create multiple evidence items with different sources
        items = []
        
        for i in range(3):
            item = EvidenceItem(
                id=f"ev_snap_{i:03d}",
                source_url=f"https://example.com/source_{i}",
                snapshot_id=f"snap_{i:03d}",
                date="2025-01-20",
                source_type="news",
                title=f"Source {i}",
                claims=[EvidenceClaim(
                    driver="growth",
                    statement=f"Growth indicator {i}",
                    direction="+",
                    magnitude_units="%",
                    magnitude_value=2.0,
                    horizon="y1",
                    confidence=0.85,
                    quote=f"Quote from source {i}"
                )]
            )
            items.append(item)
        
        return EvidenceBundle(
            research_timestamp=datetime.now().isoformat(),
            ticker=self.ticker,
            items=items
        )
    
    def _create_coverage_test_evidence(self) -> EvidenceBundle:
        """Create evidence bundle for coverage testing."""
        claims = []
        
        # Create claims for all 4 drivers
        drivers = ["growth", "margin", "wacc", "s2c"]
        for i, driver in enumerate(drivers):
            claims.append(EvidenceClaim(
                driver=driver,
                statement=f"Test {driver} claim",
                direction="+",
                magnitude_units="%" if driver in ["growth", "margin"] else "abs",
                magnitude_value=2.0 if driver in ["growth", "margin"] else 0.1,
                horizon="y1",
                confidence=0.85,
                quote=f"Quote for {driver} improvement"
            ))
        
        evidence_item = EvidenceItem(
            id="ev_coverage",
            source_url="https://example.com/comprehensive",
            snapshot_id="snap_coverage",
            date="2025-01-20",
            source_type="10K",
            title="Comprehensive Filing",
            claims=claims
        )
        
        return EvidenceBundle(
            research_timestamp=datetime.now().isoformat(),
            ticker=self.ticker,
            items=[evidence_item]
        )


# Evaluation runner
def run_evidence_evaluation():
    """Run comprehensive evidence pipeline evaluation."""
    print("🧪 Running Evidence Pipeline Evaluation")
    print("=" * 50)
    
    # Run all tests
    test_instance = TestEvidencePipelineIntegration()
    test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
    
    results = {}
    for test_method_name in test_methods:
        print(f"\n▶ Running {test_method_name}")
        
        try:
            test_instance.setup_method()
            test_method = getattr(test_instance, test_method_name)
            test_method()
            test_instance.teardown_method()
            
            results[test_method_name] = "PASS"
            print(f"  ✅ {test_method_name}: PASS")
            
        except Exception as e:
            results[test_method_name] = f"FAIL: {str(e)}"
            print(f"  ❌ {test_method_name}: FAIL - {str(e)}")
    
    # Summary
    passed = sum(1 for result in results.values() if result == "PASS")
    total = len(results)
    
    print(f"\n📊 Evaluation Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ Evidence pipeline evaluation: ALL TESTS PASSED")
        return True
    else:
        print("❌ Evidence pipeline evaluation: SOME TESTS FAILED")
        for test_name, result in results.items():
            if result != "PASS":
                print(f"  - {test_name}: {result}")
        return False


if __name__ == "__main__":
    success = run_evidence_evaluation()
    exit(0 if success else 1)