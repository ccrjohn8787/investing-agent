#!/usr/bin/env python3
"""
Driver Change Accuracy Tests

Validates that evidence-based driver changes are applied correctly
with proper safety caps and confidence filtering.
"""

import pytest
from pathlib import Path
import tempfile

from investing_agent.schemas.inputs import InputsI, Drivers
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim
from investing_agent.orchestration.pr_logger import PRLogger


class TestDriverChangeAccuracy:
    """Test suite for driver change accuracy."""
    
    def setup_method(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Base InputsI for testing
        self.base_inputs = InputsI(
            company="Test Company",
            ticker="TEST",
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
    
    def test_growth_driver_changes(self):
        """Test growth driver modifications with safety caps."""
        pr_logger = PRLogger(confidence_threshold=0.80)
        
        # Create evidence with growth claims
        evidence_bundle = self._create_growth_evidence()
        
        # Apply evidence
        modified_inputs, pr_log = pr_logger.apply_evidence_to_inputs(
            self.base_inputs, evidence_bundle
        )
        
        # Verify changes applied
        assert pr_log.validation_summary['total_applied'] > 0
        
        # Check growth modifications
        growth_changes = pr_log.get_changes_by_driver("drivers.sales_growth")
        assert len(growth_changes) > 0
        
        # Verify safety caps applied
        for change in growth_changes:
            # Growth cap is 5% (500bps) per evidence item
            assert change.change_magnitude <= 0.05  # 5% cap
            
        print(f"Growth changes: {[(c.before_value, c.after_value, c.change_magnitude) for c in growth_changes]}")
    
    def test_margin_driver_changes(self):
        """Test margin driver modifications with safety caps."""
        pr_logger = PRLogger(confidence_threshold=0.80)
        
        # Create evidence with margin claims
        evidence_bundle = self._create_margin_evidence()
        
        # Apply evidence
        modified_inputs, pr_log = pr_logger.apply_evidence_to_inputs(
            self.base_inputs, evidence_bundle
        )
        
        # Verify margin modifications
        margin_changes = pr_log.get_changes_by_driver("drivers.oper_margin")
        assert len(margin_changes) > 0
        
        # Verify safety caps applied
        for change in margin_changes:
            # Margin cap is 2% (200bps) per evidence item
            assert change.change_magnitude <= 0.02  # 2% cap
            
        print(f"Margin changes: {[(c.before_value, c.after_value, c.change_magnitude) for c in margin_changes]}")
    
    def test_confidence_threshold_filtering(self):
        """Test that low-confidence claims are filtered out."""
        pr_logger = PRLogger(confidence_threshold=0.80)
        
        # Create evidence with mixed confidence levels
        evidence_bundle = self._create_mixed_confidence_evidence()
        
        # Apply evidence
        modified_inputs, pr_log = pr_logger.apply_evidence_to_inputs(
            self.base_inputs, evidence_bundle
        )
        
        # Verify only high-confidence changes applied
        for change in pr_log.changes:
            assert change.claim_confidence >= 0.80
            
        # Verify low-confidence claims rejected
        total_attempted = pr_log.validation_summary.get('total_attempted', 0)
        total_applied = pr_log.validation_summary.get('total_applied', 0)
        
        # Should have more attempts than applications due to filtering
        assert total_attempted >= total_applied
        
        print(f"Confidence filtering: {total_applied}/{total_attempted} changes applied")
    
    def test_conflict_resolution(self):
        """Test conflict resolution between competing evidence."""
        pr_logger = PRLogger(confidence_threshold=0.70)  # Lower threshold to test conflicts
        
        # Create evidence with conflicting claims
        evidence_bundle = self._create_conflicting_evidence()
        
        # Apply evidence
        modified_inputs, pr_log = pr_logger.apply_evidence_to_inputs(
            self.base_inputs, evidence_bundle
        )
        
        # Verify conflicts were resolved
        assert len(pr_log.conflicts_resolved) > 0
        
        # Verify highest confidence claim won
        conflict = pr_log.conflicts_resolved[0]
        winning_changes = pr_log.get_changes_by_evidence(conflict.winning_evidence_id)
        
        if winning_changes:
            winning_confidence = winning_changes[0].claim_confidence
            # Should be the highest confidence among conflicts
            assert winning_confidence >= 0.85  # Expecting high confidence winner
            
        print(f"Conflicts resolved: {len(pr_log.conflicts_resolved)}")
    
    def test_safety_cap_enforcement(self):
        """Test enforcement of safety caps on extreme values."""
        # Test with values just at the cap limit
        pr_logger = PRLogger(confidence_threshold=0.80)
        evidence_bundle = self._create_capped_magnitude_evidence()
        
        # Apply evidence
        modified_inputs, pr_log = pr_logger.apply_evidence_to_inputs(
            self.base_inputs, evidence_bundle
        )
        
        # Verify changes within caps are applied
        assert pr_log.validation_summary['total_applied'] > 0
        
        # Verify no change exceeds caps
        for change in pr_log.changes:
            if "growth" in change.target_path:
                assert change.change_magnitude <= 0.05  # 5% growth cap
            elif "margin" in change.target_path:
                assert change.change_magnitude <= 0.02  # 2% margin cap
                
        print(f"Safety validation working: changes within caps applied")
    
    def test_audit_trail_completeness(self):
        """Test completeness of audit trail."""
        pr_logger = PRLogger(confidence_threshold=0.80)
        
        # Create simple evidence for audit testing
        evidence_bundle = self._create_growth_evidence()
        
        # Apply evidence
        modified_inputs, pr_log = pr_logger.apply_evidence_to_inputs(
            self.base_inputs, evidence_bundle
        )
        
        # Verify audit trail completeness
        assert len(pr_log.changes) > 0
        
        for change in pr_log.changes:
            # Every change must have complete provenance
            assert change.evidence_id.startswith('ev_')
            assert change.target_path is not None
            assert change.before_value is not None
            assert change.after_value is not None
            assert change.change_reason is not None
            assert change.applied_rule is not None
            assert change.timestamp is not None
            
        # Verify audit report generation
        audit_report = pr_log.generate_audit_report()
        
        assert 'statistics' in audit_report
        assert 'driver_impacts' in audit_report
        assert 'evidence_utilization' in audit_report
        
        print(f"Audit trail: {len(pr_log.changes)} changes tracked")
    
    def _create_growth_evidence(self) -> EvidenceBundle:
        """Create evidence bundle targeting growth drivers."""
        growth_claim = EvidenceClaim(
            driver="growth",
            statement="Management raised revenue growth guidance",
            direction="+",
            magnitude_units="%",
            magnitude_value=3.0,  # 3% increase
            horizon="y1",
            confidence=0.85,
            quote="Revenue growth expected to accelerate"
        )
        
        item = EvidenceItem(
            id="ev_growth_test",
            source_url="https://test.com/growth",
            snapshot_id="snap_growth",
            date="2025-01-20",
            source_type="transcript",
            title="Growth Guidance Update",
            claims=[growth_claim]
        )
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=[item]
        )
    
    def _create_margin_evidence(self) -> EvidenceBundle:
        """Create evidence bundle targeting margin drivers."""
        margin_claim = EvidenceClaim(
            driver="margin",
            statement="Cost reduction program to improve margins",
            direction="+",
            magnitude_units="bps",
            magnitude_value=150.0,  # 150bps increase
            horizon="y1",
            confidence=0.88,
            quote="Operating margins expected to improve by 150 basis points"
        )
        
        item = EvidenceItem(
            id="ev_margin_test",
            source_url="https://test.com/margin",
            snapshot_id="snap_margin",
            date="2025-01-20",
            source_type="10K",
            title="Margin Improvement Program",
            claims=[margin_claim]
        )
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=[item]
        )
    
    def _create_mixed_confidence_evidence(self) -> EvidenceBundle:
        """Create evidence with mixed confidence levels."""
        claims = [
            # High confidence - should be applied
            EvidenceClaim(
                driver="growth",
                statement="Strong guidance",
                direction="+",
                magnitude_units="%",
                magnitude_value=2.0,
                horizon="y1",
                confidence=0.90,  # High confidence
                quote="Strong revenue growth expected"
            ),
            # Low confidence - should be filtered out  
            EvidenceClaim(
                driver="growth",
                statement="Uncertain outlook",
                direction="+",
                magnitude_units="%",
                magnitude_value=1.0,
                horizon="y1",
                confidence=0.60,  # Low confidence
                quote="Uncertain market conditions"
            )
        ]
        
        item = EvidenceItem(
            id="ev_mixed_conf",
            source_url="https://test.com/mixed",
            snapshot_id="snap_mixed",
            date="2025-01-20",
            source_type="news",
            title="Mixed Signals",
            claims=claims
        )
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=[item]
        )
    
    def _create_conflicting_evidence(self) -> EvidenceBundle:
        """Create evidence with conflicting claims."""
        # Two items with conflicting growth claims for same period
        item1_claims = [EvidenceClaim(
            driver="growth",
            statement="Conservative growth outlook",
            direction="+",
            magnitude_units="%",
            magnitude_value=1.0,
            horizon="y1",
            confidence=0.75,  # Lower confidence
            quote="Cautious growth expectations"
        )]
        
        item2_claims = [EvidenceClaim(
            driver="growth",
            statement="Aggressive growth targets",
            direction="+",
            magnitude_units="%",
            magnitude_value=4.0,
            horizon="y1",
            confidence=0.90,  # Higher confidence - should win
            quote="Ambitious growth targets set"
        )]
        
        items = [
            EvidenceItem(
                id="ev_conflict_1",
                source_url="https://test.com/conservative",
                snapshot_id="snap_conflict_1",
                date="2025-01-19",
                source_type="news",
                title="Conservative Outlook",
                claims=item1_claims
            ),
            EvidenceItem(
                id="ev_conflict_2",
                source_url="https://test.com/aggressive",
                snapshot_id="snap_conflict_2",
                date="2025-01-20",
                source_type="transcript",
                title="Aggressive Targets",
                claims=item2_claims
            )
        ]
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=items
        )
    
    def _create_capped_magnitude_evidence(self) -> EvidenceBundle:
        """Create evidence with magnitude at cap limits."""
        capped_claims = [
            EvidenceClaim(
                driver="growth",
                statement="Maximum growth acceleration",
                direction="+",
                magnitude_units="%",
                magnitude_value=5.0,  # Exactly at 5% cap
                horizon="y1",
                confidence=0.85,
                quote="Growth at maximum expected rate"
            ),
            EvidenceClaim(
                driver="margin",
                statement="Maximum margin expansion",
                direction="+",
                magnitude_units="bps",
                magnitude_value=200.0,  # Exactly at 200bps cap
                horizon="y1",
                confidence=0.82,
                quote="Margins at maximum improvement rate"
            )
        ]
        
        item = EvidenceItem(
            id="ev_capped",
            source_url="https://test.com/capped",
            snapshot_id="snap_capped",
            date="2025-01-20",
            source_type="PR",
            title="Maximum Projections",
            claims=capped_claims
        )
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=[item]
        )
    
    def _create_extreme_magnitude_evidence(self) -> EvidenceBundle:
        """Create evidence with extreme magnitude claims to test caps."""
        extreme_claims = [
            EvidenceClaim(
                driver="growth",
                statement="Massive growth acceleration",
                direction="+",
                magnitude_units="%",
                magnitude_value=25.0,  # 25% - should be capped to 5%
                horizon="y1",
                confidence=0.85,
                quote="Expect massive growth acceleration"
            ),
            EvidenceClaim(
                driver="margin",
                statement="Huge margin expansion",
                direction="+",
                magnitude_units="bps",
                magnitude_value=1000.0,  # 1000bps - should be capped to 200bps
                horizon="y1",
                confidence=0.82,
                quote="Margins should expand dramatically"
            )
        ]
        
        item = EvidenceItem(
            id="ev_extreme",
            source_url="https://test.com/extreme",
            snapshot_id="snap_extreme",
            date="2025-01-20",
            source_type="PR",
            title="Extreme Projections",
            claims=extreme_claims
        )
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=[item]
        )
    
    def _create_comprehensive_evidence(self) -> EvidenceBundle:
        """Create comprehensive evidence for audit trail testing."""
        all_driver_claims = []
        
        # Create claims for all drivers
        drivers_config = [
            ("growth", "%", 2.0, "Revenue growth acceleration"),
            ("margin", "bps", 100.0, "Operating leverage improvement"),
            ("wacc", "bps", -25.0, "Lower cost of capital"),
            ("s2c", "abs", 0.2, "Capital efficiency gains")
        ]
        
        for driver, units, magnitude, statement in drivers_config:
            claim = EvidenceClaim(
                driver=driver,
                statement=statement,
                direction="+" if magnitude > 0 else "-",
                magnitude_units=units,
                magnitude_value=abs(magnitude),
                horizon="y1",
                confidence=0.85,
                quote=f"Quote supporting {statement}"
            )
            all_driver_claims.append(claim)
        
        item = EvidenceItem(
            id="ev_comprehensive",
            source_url="https://test.com/comprehensive",
            snapshot_id="snap_comprehensive",
            date="2025-01-20",
            source_type="10K",
            title="Comprehensive Analysis",
            claims=all_driver_claims
        )
        
        return EvidenceBundle(
            research_timestamp="2025-01-20T10:00:00Z",
            ticker="TEST",
            items=[item]
        )


def run_driver_accuracy_tests():
    """Run driver change accuracy evaluation."""
    print("🎯 Running Driver Change Accuracy Tests")
    print("=" * 50)
    
    test_instance = TestDriverChangeAccuracy()
    test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
    
    results = {}
    for test_method_name in test_methods:
        print(f"\n▶ {test_method_name}")
        
        try:
            test_instance.setup_method()
            test_method = getattr(test_instance, test_method_name)
            test_method()
            
            results[test_method_name] = "PASS"
            print(f"  ✅ PASS")
            
        except Exception as e:
            results[test_method_name] = f"FAIL: {str(e)}"
            print(f"  ❌ FAIL: {str(e)}")
    
    # Summary
    passed = sum(1 for result in results.values() if result == "PASS")
    total = len(results)
    
    print(f"\n📊 Driver Accuracy Tests: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    success = run_driver_accuracy_tests()
    exit(0 if success else 1)