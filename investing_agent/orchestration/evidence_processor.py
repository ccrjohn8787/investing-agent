from __future__ import annotations

"""
Evidence Ingestion Engine

Processes evidence bundles into InputsI driver modifications with
safety caps, conflict resolution, and complete audit trail via Model-PR log.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import copy

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.evidence import EvidenceBundle, EvidenceClaim, validate_evidence_bundle
from investing_agent.schemas.model_pr_log import ModelPRLog, DriverChange, ValidationResult
from investing_agent.orchestration.pr_logger import PRLogger


class EvidenceProcessor:
    """Engine for ingesting evidence into InputsI with validation and logging."""
    
    def __init__(
        self,
        confidence_threshold: float = 0.80,
        enable_safety_caps: bool = True,
        max_growth_change_bps: float = 500.0,  # 5%
        max_margin_change_bps: float = 200.0   # 2%
    ):
        """Initialize evidence processor with safety configuration."""
        self.confidence_threshold = confidence_threshold
        self.enable_safety_caps = enable_safety_caps
        self.max_growth_change_bps = max_growth_change_bps
        self.max_margin_change_bps = max_margin_change_bps
        self.pr_logger = PRLogger(confidence_threshold)
    
    def ingest_evidence(
        self,
        inputs: InputsI,
        evidence_bundle: EvidenceBundle,
        dry_run: bool = False,
        output_dir: Optional[Path] = None
    ) -> Tuple[InputsI, ModelPRLog, Dict[str, Any]]:
        """
        Ingest evidence bundle into InputsI with complete audit trail.
        
        Args:
            inputs: Original InputsI to modify
            evidence_bundle: Evidence bundle with claims to apply
            dry_run: If True, don't actually modify inputs
            output_dir: Directory to save logs (optional)
            
        Returns:
            Tuple of (modified_inputs, pr_log, processing_summary)
        """
        # Validate evidence bundle quality
        validation_result = validate_evidence_bundle(evidence_bundle, self.confidence_threshold)
        
        if not validation_result.is_valid:
            raise ValueError(f"Evidence bundle failed validation: {validation_result.issues}")
        
        # Apply evidence using PR Logger
        modified_inputs, pr_log = self.pr_logger.apply_evidence_to_inputs(
            inputs, evidence_bundle, dry_run
        )
        
        # Generate processing summary
        processing_summary = self._generate_processing_summary(
            evidence_bundle, pr_log, validation_result
        )
        
        # Save logs if output directory provided
        if output_dir and not dry_run:
            self._save_processing_artifacts(output_dir, pr_log, evidence_bundle, processing_summary)
        
        return modified_inputs, pr_log, processing_summary
    
    def validate_evidence_quality(
        self, 
        evidence_bundle: EvidenceBundle
    ) -> Dict[str, Any]:
        """Comprehensive evidence quality validation."""
        validation_result = validate_evidence_bundle(evidence_bundle, self.confidence_threshold)
        
        # Additional quality checks
        quality_metrics = {
            'bundle_validation': validation_result.dict(),
            'temporal_coverage': self._analyze_temporal_coverage(evidence_bundle),
            'source_diversity': self._analyze_source_diversity(evidence_bundle),
            'driver_balance': self._analyze_driver_balance(evidence_bundle),
            'confidence_distribution': self._analyze_confidence_distribution(evidence_bundle)
        }
        
        return quality_metrics
    
    def _analyze_temporal_coverage(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """Analyze temporal distribution of evidence."""
        dates = []
        for item in evidence_bundle.items:
            if item.date:
                try:
                    date_obj = datetime.strptime(item.date, '%Y-%m-%d')
                    dates.append(date_obj)
                except ValueError:
                    continue
        
        if not dates:
            return {'status': 'no_dates', 'coverage_days': 0}
        
        dates.sort()
        coverage_days = (dates[-1] - dates[0]).days
        
        return {
            'status': 'valid' if coverage_days <= 90 else 'stale',
            'coverage_days': coverage_days,
            'earliest_date': dates[0].isoformat(),
            'latest_date': dates[-1].isoformat(),
            'total_dated_items': len(dates)
        }
    
    def _analyze_source_diversity(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """Analyze diversity of evidence sources."""
        source_types = {}
        domains = set()
        
        for item in evidence_bundle.items:
            # Count source types
            source_type = item.source_type
            source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # Extract domains
            try:
                from urllib.parse import urlparse
                domain = urlparse(item.source_url).netloc
                domains.add(domain)
            except Exception:
                pass
        
        return {
            'source_types': source_types,
            'unique_domains': len(domains),
            'diversity_score': len(source_types) + (len(domains) * 0.5),
            'is_diverse': len(source_types) >= 2 and len(domains) >= 3
        }
    
    def _analyze_driver_balance(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """Analyze balance of evidence across valuation drivers."""
        driver_counts = {'growth': 0, 'margin': 0, 'wacc': 0, 's2c': 0}
        driver_confidence = {'growth': [], 'margin': [], 'wacc': [], 's2c': []}
        
        for item in evidence_bundle.items:
            for claim in item.claims:
                if claim.confidence >= self.confidence_threshold:
                    driver_counts[claim.driver] += 1
                    driver_confidence[claim.driver].append(claim.confidence)
        
        # Calculate average confidence per driver
        avg_confidence = {}
        for driver, confidences in driver_confidence.items():
            avg_confidence[driver] = sum(confidences) / len(confidences) if confidences else 0.0
        
        total_claims = sum(driver_counts.values())
        coverage_ratio = sum(1 for count in driver_counts.values() if count > 0) / 4.0
        
        return {
            'driver_counts': driver_counts,
            'average_confidence': avg_confidence,
            'total_high_confidence_claims': total_claims,
            'coverage_ratio': coverage_ratio,
            'is_balanced': coverage_ratio >= 0.5 and total_claims >= 4
        }
    
    def _analyze_confidence_distribution(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """Analyze distribution of confidence scores."""
        all_confidences = []
        for item in evidence_bundle.items:
            for claim in item.claims:
                all_confidences.append(claim.confidence)
        
        if not all_confidences:
            return {'status': 'no_claims'}
        
        # Calculate statistics
        avg_confidence = sum(all_confidences) / len(all_confidences)
        min_confidence = min(all_confidences)
        max_confidence = max(all_confidences)
        
        # Count by threshold buckets
        high_conf = sum(1 for c in all_confidences if c >= 0.8)
        med_conf = sum(1 for c in all_confidences if 0.6 <= c < 0.8)
        low_conf = sum(1 for c in all_confidences if c < 0.6)
        
        return {
            'average_confidence': avg_confidence,
            'min_confidence': min_confidence,
            'max_confidence': max_confidence,
            'total_claims': len(all_confidences),
            'high_confidence_count': high_conf,
            'medium_confidence_count': med_conf,
            'low_confidence_count': low_conf,
            'quality_ratio': high_conf / len(all_confidences)
        }
    
    def _generate_processing_summary(
        self,
        evidence_bundle: EvidenceBundle,
        pr_log: ModelPRLog,
        validation_result: Any
    ) -> Dict[str, Any]:
        """Generate comprehensive processing summary."""
        
        # Driver impact analysis
        driver_impacts = {}
        for change in pr_log.changes:
            driver_path = change.target_path.split('[')[0]  # Remove array indices
            if driver_path not in driver_impacts:
                driver_impacts[driver_path] = {
                    'changes_applied': 0,
                    'total_magnitude': 0.0,
                    'avg_confidence': 0.0,
                    'evidence_items': []
                }
            
            driver_impacts[driver_path]['changes_applied'] += 1
            driver_impacts[driver_path]['total_magnitude'] += change.change_magnitude
            driver_impacts[driver_path]['evidence_items'].append(change.evidence_id)
        
        # Calculate average confidence per driver
        for driver_path, impact in driver_impacts.items():
            relevant_changes = [c for c in pr_log.changes if c.target_path.startswith(driver_path)]
            if relevant_changes:
                impact['avg_confidence'] = sum(c.claim_confidence for c in relevant_changes) / len(relevant_changes)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'evidence_bundle_stats': {
                'total_items': len(evidence_bundle.items),
                'total_claims': sum(len(item.claims) for item in evidence_bundle.items),
                'frozen': evidence_bundle.frozen
            },
            'processing_stats': {
                'changes_attempted': pr_log.validation_summary.get('total_attempted', 0),
                'changes_applied': pr_log.validation_summary.get('total_applied', 0),
                'changes_rejected': pr_log.validation_summary.get('total_rejected', 0),
                'conflicts_resolved': len(pr_log.conflicts_resolved)
            },
            'driver_impacts': driver_impacts,
            'validation_result': validation_result.dict(),
            'quality_score': self._calculate_overall_quality_score(evidence_bundle, pr_log)
        }
    
    def _calculate_overall_quality_score(
        self, 
        evidence_bundle: EvidenceBundle, 
        pr_log: ModelPRLog
    ) -> float:
        """Calculate overall quality score (0.0-1.0) for evidence processing."""
        score_components = []
        
        # Evidence coverage score
        high_conf_claims = len(evidence_bundle.get_high_confidence_claims(self.confidence_threshold))
        total_claims = sum(len(item.claims) for item in evidence_bundle.items)
        coverage_score = min(1.0, high_conf_claims / max(total_claims, 1) * 2)  # Up to 2x multiplier
        score_components.append(coverage_score * 0.3)
        
        # Driver diversity score
        drivers_affected = set()
        for change in pr_log.changes:
            driver = change.target_path.split('.')[1].split('[')[0]  # Extract driver name
            drivers_affected.add(driver)
        diversity_score = len(drivers_affected) / 4.0  # 4 possible drivers
        score_components.append(diversity_score * 0.2)
        
        # Application success rate
        total_attempted = pr_log.validation_summary.get('total_attempted', 0)
        total_applied = pr_log.validation_summary.get('total_applied', 0)
        success_rate = total_applied / max(total_attempted, 1)
        score_components.append(success_rate * 0.3)
        
        # Average confidence score
        if pr_log.changes:
            avg_confidence = sum(c.claim_confidence for c in pr_log.changes) / len(pr_log.changes)
        else:
            avg_confidence = 0.0
        score_components.append(avg_confidence * 0.2)
        
        return sum(score_components)
    
    def _save_processing_artifacts(
        self,
        output_dir: Path,
        pr_log: ModelPRLog,
        evidence_bundle: EvidenceBundle,
        processing_summary: Dict[str, Any]
    ) -> None:
        """Save processing artifacts to output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Model-PR log
        pr_log_path = self.pr_logger.save_log(output_dir, f"model_pr_log_{pr_log.ticker}.json")
        
        # Save evidence bundle
        evidence_path = output_dir / f"evidence_bundle_{evidence_bundle.ticker}.json"
        with open(evidence_path, 'w') as f:
            json.dump(evidence_bundle.dict(), f, indent=2, default=str)
        
        # Save processing summary
        summary_path = output_dir / f"processing_summary_{evidence_bundle.ticker}.json"
        with open(summary_path, 'w') as f:
            json.dump(processing_summary, f, indent=2, default=str)
        
        print(f"Saved processing artifacts to {output_dir}")
        print(f"  - PR Log: {pr_log_path}")
        print(f"  - Evidence Bundle: {evidence_path}")
        print(f"  - Processing Summary: {summary_path}")


# Convenience functions
def process_evidence_bundle(
    inputs: InputsI,
    evidence_bundle: EvidenceBundle,
    confidence_threshold: float = 0.80,
    dry_run: bool = False,
    output_dir: Optional[Path] = None
) -> Tuple[InputsI, ModelPRLog, Dict[str, Any]]:
    """Process evidence bundle with default configuration."""
    processor = EvidenceProcessor(confidence_threshold=confidence_threshold)
    return processor.ingest_evidence(inputs, evidence_bundle, dry_run, output_dir)


def validate_evidence_bundle_quality(evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
    """Validate evidence bundle quality with default configuration."""
    processor = EvidenceProcessor()
    return processor.validate_evidence_quality(evidence_bundle)