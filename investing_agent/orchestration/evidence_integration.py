from __future__ import annotations

"""
Evidence Pipeline Integration

Integrates evidence-based research system with existing report generation pipeline.
Provides backward compatibility while enabling research-once-then-freeze workflow.
"""

from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from datetime import datetime
import json

from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.evidence import EvidenceBundle
from investing_agent.schemas.model_pr_log import ModelPRLog
from investing_agent.agents.research_unified import ResearchUnified, generate_evidence_bundle
from investing_agent.orchestration.evidence_processor import EvidenceProcessor
from investing_agent.orchestration.evidence_freezer import EvidenceFreezer
from investing_agent.connectors.snapshot_manager import SnapshotManager
from investing_agent.orchestration.manifest import Manifest


class EvidenceIntegrationManager:
    """Manages integration of evidence pipeline with existing report generation."""
    
    def __init__(
        self,
        confidence_threshold: float = 0.80,
        enable_evidence_pipeline: bool = True,
        output_dir: Optional[Path] = None
    ):
        """Initialize integration manager."""
        self.confidence_threshold = confidence_threshold
        self.enable_evidence_pipeline = enable_evidence_pipeline
        self.output_dir = output_dir or Path("out")
        
        # Initialize components
        self.research_agent = ResearchUnified(confidence_threshold)
        self.evidence_processor = EvidenceProcessor(confidence_threshold)
        self.evidence_freezer = EvidenceFreezer()
        self.snapshot_manager = SnapshotManager(self.output_dir / "snapshots")
    
    def execute_evidence_enhanced_research(
        self,
        ticker: str,
        inputs: InputsI,
        manifest: Manifest,
        cassette_path: Optional[str] = None,
        force_new_research: bool = False
    ) -> Tuple[InputsI, Dict[str, Any]]:
        """
        Execute evidence-enhanced research with integration to existing pipeline.
        
        Args:
            ticker: Stock ticker
            inputs: Current InputsI (will be modified with evidence)
            manifest: Manifest for logging
            cassette_path: Path for deterministic testing
            force_new_research: Force new research even if evidence exists
            
        Returns:
            Tuple of (modified_inputs, evidence_artifacts)
        """
        evidence_artifacts = {
            'evidence_bundle': None,
            'model_pr_log': None,
            'processing_summary': None,
            'frozen_evidence_path': None
        }
        
        if not self.enable_evidence_pipeline:
            # Return unchanged inputs for backward compatibility
            return inputs, evidence_artifacts
        
        # Check for existing frozen evidence
        frozen_evidence_path = self._find_existing_frozen_evidence(ticker)
        
        if frozen_evidence_path and not force_new_research:
            # Use existing frozen evidence
            evidence_bundle = self.evidence_freezer.load_frozen_evidence(frozen_evidence_path)
            print(f"Using existing frozen evidence from {frozen_evidence_path}")
            
            evidence_artifacts['evidence_bundle'] = evidence_bundle
            evidence_artifacts['frozen_evidence_path'] = frozen_evidence_path
            
            # Apply evidence to inputs (should be deterministic)
            modified_inputs, pr_log, processing_summary = self.evidence_processor.ingest_evidence(
                inputs, evidence_bundle, dry_run=False, output_dir=self.output_dir / ticker / "evidence"
            )
            
            evidence_artifacts['model_pr_log'] = pr_log
            evidence_artifacts['processing_summary'] = processing_summary
            
        else:
            # Execute new research pass
            print(f"Executing new research pass for {ticker}")
            
            # Generate evidence bundle
            evidence_bundle = self.research_agent.execute_research_pass(
                ticker, inputs, sources=None, cassette_path=cassette_path
            )
            
            if not evidence_bundle.items:
                print(f"No evidence found for {ticker}, returning unchanged inputs")
                return inputs, evidence_artifacts
            
            # Process evidence into inputs
            modified_inputs, pr_log, processing_summary = self.evidence_processor.ingest_evidence(
                inputs, evidence_bundle, dry_run=False, output_dir=self.output_dir / ticker / "evidence"
            )
            
            # Freeze evidence bundle
            frozen_evidence = self.evidence_freezer.freeze_evidence_bundle(
                evidence_bundle, manifest, f"Research pass completed for {ticker}"
            )
            
            # Save frozen evidence
            frozen_evidence_path = self.evidence_freezer.save_frozen_evidence(
                frozen_evidence, self.output_dir / ticker / "evidence"
            )
            
            evidence_artifacts.update({
                'evidence_bundle': frozen_evidence,
                'model_pr_log': pr_log,
                'processing_summary': processing_summary,
                'frozen_evidence_path': frozen_evidence_path
            })
            
            print(f"Evidence pipeline completed: {pr_log.validation_summary.get('total_applied', 0)} changes applied")
        
        # Log to manifest
        self._log_evidence_to_manifest(manifest, evidence_artifacts, ticker)
        
        return modified_inputs, evidence_artifacts
    
    def create_narrative_evidence_context(
        self, 
        evidence_artifacts: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create evidence context for narrative generation (backward compatible).
        
        Args:
            evidence_artifacts: Evidence artifacts from research
            
        Returns:
            Evidence context compatible with existing writer agents
        """
        if not evidence_artifacts.get('evidence_bundle'):
            return None
        
        evidence_bundle = evidence_artifacts['evidence_bundle']
        
        # Create read-only access for narrative agents
        read_only_access = self.evidence_freezer.create_read_only_access(evidence_bundle)
        
        # Format for compatibility with existing writer
        narrative_context = {
            'evidence_available': True,
            'total_evidence_items': len(evidence_bundle.items),
            'high_confidence_claims': len(evidence_bundle.get_high_confidence_claims(self.confidence_threshold)),
            'frozen_timestamp': evidence_bundle.freeze_timestamp,
            'access_token': self.evidence_freezer.create_narrative_access_token(evidence_bundle, "writer"),
            
            # Backward compatibility with existing insights format
            'insights_bundle': self._convert_to_insights_format(evidence_bundle),
            'citations_available': read_only_access.get_claims_for_citation(),
            
            # Evidence summary for narrative
            'evidence_summary': self._create_evidence_summary(evidence_bundle)
        }
        
        return narrative_context
    
    def validate_pipeline_integration(self, ticker: str) -> Dict[str, Any]:
        """
        Validate evidence pipeline integration for ticker.
        
        Returns:
            Integration validation results
        """
        validation_results = {
            'ticker': ticker,
            'validation_timestamp': datetime.now().isoformat(),
            'pipeline_enabled': self.enable_evidence_pipeline,
            'components_available': {},
            'existing_evidence': {},
            'integration_status': 'unknown'
        }
        
        # Check component availability
        try:
            self.research_agent
            validation_results['components_available']['research_agent'] = True
        except Exception as e:
            validation_results['components_available']['research_agent'] = f"Error: {str(e)}"
        
        try:
            self.evidence_processor
            validation_results['components_available']['evidence_processor'] = True
        except Exception as e:
            validation_results['components_available']['evidence_processor'] = f"Error: {str(e)}"
        
        # Check for existing evidence
        frozen_evidence_path = self._find_existing_frozen_evidence(ticker)
        if frozen_evidence_path:
            try:
                evidence_bundle = self.evidence_freezer.load_frozen_evidence(frozen_evidence_path)
                integrity = self.evidence_freezer.verify_freeze_integrity(evidence_bundle)
                
                validation_results['existing_evidence'] = {
                    'path': str(frozen_evidence_path),
                    'integrity_valid': integrity['is_valid'],
                    'total_items': len(evidence_bundle.items),
                    'freeze_timestamp': evidence_bundle.freeze_timestamp
                }
            except Exception as e:
                validation_results['existing_evidence'] = {'error': str(e)}
        
        # Determine integration status
        all_components_ok = all(
            status is True for status in validation_results['components_available'].values()
        )
        
        if all_components_ok:
            if self.enable_evidence_pipeline:
                validation_results['integration_status'] = 'active'
            else:
                validation_results['integration_status'] = 'available_but_disabled'
        else:
            validation_results['integration_status'] = 'component_errors'
        
        return validation_results
    
    def _find_existing_frozen_evidence(self, ticker: str) -> Optional[Path]:
        """Find existing frozen evidence for ticker."""
        evidence_dir = self.output_dir / ticker / "evidence"
        if not evidence_dir.exists():
            return None
        
        # Look for frozen evidence files
        frozen_files = list(evidence_dir.glob(f"frozen_evidence_{ticker}_*.json"))
        
        if frozen_files:
            # Return most recent frozen evidence
            return max(frozen_files, key=lambda p: p.stat().st_mtime)
        
        return None
    
    def _convert_to_insights_format(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """Convert evidence bundle to existing insights format for compatibility."""
        insights_cards = []
        
        for item in evidence_bundle.items:
            for claim in item.claims:
                if claim.confidence >= self.confidence_threshold:
                    insights_cards.append({
                        'claim': claim.statement,
                        'tags': [claim.driver],
                        'start_year_offset': 0 if claim.horizon == "y1" else 1,
                        'end_year_offset': 1 if claim.horizon == "y2-3" else 0,
                        'confidence': claim.confidence,
                        'quotes': [{
                            'text': claim.quote,
                            'snapshot_ids': [item.snapshot_id],
                            'sources': [item.source_url]
                        }]
                    })
        
        return {'cards': insights_cards}
    
    def _create_evidence_summary(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """Create evidence summary for narrative context."""
        driver_breakdown = {'growth': 0, 'margin': 0, 'wacc': 0, 's2c': 0}
        source_types = {}
        
        for item in evidence_bundle.items:
            source_types[item.source_type] = source_types.get(item.source_type, 0) + 1
            
            for claim in item.claims:
                if claim.confidence >= self.confidence_threshold:
                    driver_breakdown[claim.driver] += 1
        
        return {
            'total_items': len(evidence_bundle.items),
            'driver_coverage': driver_breakdown,
            'source_type_breakdown': source_types,
            'research_timestamp': evidence_bundle.research_timestamp,
            'coverage_score': sum(1 for count in driver_breakdown.values() if count > 0) / 4.0
        }
    
    def _log_evidence_to_manifest(
        self, 
        manifest: Manifest, 
        evidence_artifacts: Dict[str, Any], 
        ticker: str
    ) -> None:
        """Log evidence processing to manifest."""
        if evidence_artifacts.get('model_pr_log'):
            pr_log = evidence_artifacts['model_pr_log']
            
            # Add evidence processing entry
            evidence_entry = {
                'evidence_processing': {
                    'ticker': ticker,
                    'timestamp': datetime.now().isoformat(),
                    'changes_applied': pr_log.validation_summary.get('total_applied', 0),
                    'evidence_items': len(evidence_artifacts.get('evidence_bundle', {}).items or []),
                    'frozen_evidence_path': str(evidence_artifacts.get('frozen_evidence_path', '')),
                    'model_pr_log_summary': pr_log.validation_summary
                }
            }
            
            # Add to manifest
            if not hasattr(manifest, 'evidence_processing'):
                manifest.evidence_processing = []
            manifest.evidence_processing.append(evidence_entry)


def integrate_evidence_pipeline(
    ticker: str,
    inputs: InputsI,
    manifest: Manifest,
    cassette_path: Optional[str] = None,
    output_dir: Optional[Path] = None,
    confidence_threshold: float = 0.80
) -> Tuple[InputsI, Dict[str, Any]]:
    """
    Convenience function for evidence pipeline integration.
    
    Args:
        ticker: Stock ticker
        inputs: Current InputsI
        manifest: Manifest for logging  
        cassette_path: Path for deterministic testing
        output_dir: Output directory
        confidence_threshold: Evidence confidence threshold
        
    Returns:
        Tuple of (modified_inputs, evidence_artifacts)
    """
    integration_manager = EvidenceIntegrationManager(
        confidence_threshold=confidence_threshold,
        output_dir=output_dir or Path("out")
    )
    
    return integration_manager.execute_evidence_enhanced_research(
        ticker, inputs, manifest, cassette_path
    )


def create_evidence_narrative_context(evidence_artifacts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create narrative context from evidence artifacts."""
    integration_manager = EvidenceIntegrationManager()
    return integration_manager.create_narrative_evidence_context(evidence_artifacts)