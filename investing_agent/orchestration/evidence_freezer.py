from __future__ import annotations

"""
Evidence Freezing Mechanism

Ensures evidence bundles become immutable after initial research pass,
preventing run-to-run value drift while allowing narrative content generation.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import json
import hashlib

from investing_agent.schemas.evidence import EvidenceBundle, validate_evidence_bundle
from investing_agent.orchestration.manifest import Manifest


class EvidenceFreezer:
    """Manages evidence bundle freezing and immutability enforcement."""
    
    def __init__(self, manifest_integration: bool = True):
        """Initialize evidence freezer with configuration."""
        self.manifest_integration = manifest_integration
    
    def freeze_evidence_bundle(
        self,
        evidence_bundle: EvidenceBundle,
        manifest: Optional[Manifest] = None,
        freeze_reason: str = "Research pass completed"
    ) -> EvidenceBundle:
        """
        Freeze evidence bundle making it immutable.
        
        Args:
            evidence_bundle: Bundle to freeze
            manifest: Optional manifest for logging
            freeze_reason: Reason for freezing
            
        Returns:
            Frozen evidence bundle
        """
        if evidence_bundle.frozen:
            raise ValueError(f"Evidence bundle for {evidence_bundle.ticker} is already frozen")
        
        # Validate evidence quality before freezing
        validation_result = validate_evidence_bundle(evidence_bundle)
        if not validation_result.is_valid:
            raise ValueError(f"Cannot freeze invalid evidence bundle: {validation_result.issues}")
        
        # Mark as frozen with timestamp and content hash
        evidence_bundle.freeze()
        
        # Log to manifest if provided
        if manifest and self.manifest_integration:
            self._log_freeze_to_manifest(evidence_bundle, manifest, freeze_reason)
        
        return evidence_bundle
    
    def verify_freeze_integrity(self, evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
        """
        Verify integrity of frozen evidence bundle.
        
        Returns:
            Integrity verification result
        """
        if not evidence_bundle.frozen:
            return {
                'status': 'not_frozen',
                'is_valid': True,
                'message': 'Evidence bundle is not frozen'
            }
        
        # Verify content hash
        integrity_valid = evidence_bundle.validate_integrity()
        
        # Additional checks
        checks = {
            'has_freeze_timestamp': evidence_bundle.freeze_timestamp is not None,
            'has_content_hash': evidence_bundle.content_hash is not None,
            'content_hash_valid': integrity_valid,
            'has_evidence_items': len(evidence_bundle.items) > 0
        }
        
        all_checks_pass = all(checks.values())
        
        return {
            'status': 'valid' if all_checks_pass else 'corrupted',
            'is_valid': all_checks_pass,
            'checks': checks,
            'freeze_timestamp': evidence_bundle.freeze_timestamp,
            'content_hash': evidence_bundle.content_hash,
            'message': 'Frozen evidence bundle integrity verified' if all_checks_pass else 'Evidence bundle integrity compromised'
        }
    
    def create_read_only_access(self, evidence_bundle: EvidenceBundle) -> 'ReadOnlyEvidenceAccess':
        """
        Create read-only access wrapper for frozen evidence.
        
        Returns:
            Read-only access object
        """
        if not evidence_bundle.frozen:
            raise ValueError("Evidence bundle must be frozen for read-only access")
        
        return ReadOnlyEvidenceAccess(evidence_bundle)
    
    def attempt_modification_check(
        self, 
        evidence_bundle: EvidenceBundle,
        operation: str = "modification"
    ) -> None:
        """
        Check if modification is allowed, raise exception if frozen.
        
        Args:
            evidence_bundle: Bundle to check
            operation: Description of attempted operation
        """
        if evidence_bundle.frozen:
            raise RuntimeError(
                f"Cannot perform {operation} on frozen evidence bundle. "
                f"Bundle was frozen at {evidence_bundle.freeze_timestamp}. "
                f"Create new research pass for additional evidence."
            )
    
    def create_narrative_access_token(
        self,
        evidence_bundle: EvidenceBundle,
        requesting_agent: str = "writer"
    ) -> Dict[str, Any]:
        """
        Create access token for narrative agents to read frozen evidence.
        
        Args:
            evidence_bundle: Frozen evidence bundle
            requesting_agent: Agent requesting access
            
        Returns:
            Access token with read permissions
        """
        if not evidence_bundle.frozen:
            raise ValueError("Access tokens only available for frozen evidence")
        
        # Verify integrity before granting access
        integrity = self.verify_freeze_integrity(evidence_bundle)
        if not integrity['is_valid']:
            raise ValueError("Cannot grant access to corrupted evidence bundle")
        
        access_token = {
            'token_id': hashlib.md5(f"{evidence_bundle.ticker}_{evidence_bundle.freeze_timestamp}_{requesting_agent}".encode()).hexdigest(),
            'evidence_bundle_id': f"{evidence_bundle.ticker}_{evidence_bundle.research_timestamp}",
            'requesting_agent': requesting_agent,
            'granted_at': datetime.now().isoformat(),
            'permissions': ['read_claims', 'read_metadata', 'generate_citations'],
            'restrictions': ['no_modifications', 'no_new_research'],
            'content_hash': evidence_bundle.content_hash,
            'expires_at': None  # Never expires for frozen evidence
        }
        
        return access_token
    
    def save_frozen_evidence(
        self,
        evidence_bundle: EvidenceBundle,
        output_dir: Path,
        include_integrity_proof: bool = True
    ) -> Path:
        """
        Save frozen evidence bundle with integrity proof.
        
        Args:
            evidence_bundle: Frozen evidence bundle
            output_dir: Directory to save to
            include_integrity_proof: Whether to include integrity verification
            
        Returns:
            Path to saved evidence file
        """
        if not evidence_bundle.frozen:
            raise ValueError("Can only save frozen evidence bundles")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare save data
        save_data = evidence_bundle.dict()
        
        if include_integrity_proof:
            # Add integrity proof
            integrity_result = self.verify_freeze_integrity(evidence_bundle)
            save_data['integrity_proof'] = {
                'verified_at': datetime.now().isoformat(),
                'verification_result': integrity_result,
                'freezer_version': '1.0'
            }
        
        # Save to file
        filename = f"frozen_evidence_{evidence_bundle.ticker}_{evidence_bundle.research_timestamp.replace(':', '-')}.json"
        file_path = output_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)
        
        return file_path
    
    def load_frozen_evidence(
        self,
        file_path: Path,
        verify_integrity: bool = True
    ) -> EvidenceBundle:
        """
        Load frozen evidence bundle from file with integrity verification.
        
        Args:
            file_path: Path to evidence file
            verify_integrity: Whether to verify integrity on load
            
        Returns:
            Loaded evidence bundle
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Remove integrity proof if present (not part of schema)
        integrity_proof = data.pop('integrity_proof', None)
        
        # Load evidence bundle
        evidence_bundle = EvidenceBundle(**data)
        
        if not evidence_bundle.frozen:
            raise ValueError(f"Loaded evidence bundle from {file_path} is not frozen")
        
        if verify_integrity:
            integrity_result = self.verify_freeze_integrity(evidence_bundle)
            if not integrity_result['is_valid']:
                raise ValueError(f"Loaded evidence bundle failed integrity check: {integrity_result['message']}")
        
        return evidence_bundle
    
    def _log_freeze_to_manifest(
        self,
        evidence_bundle: EvidenceBundle,
        manifest: Manifest,
        freeze_reason: str
    ) -> None:
        """Log evidence freeze action to manifest."""
        freeze_entry = {
            'action': 'evidence_freeze',
            'timestamp': evidence_bundle.freeze_timestamp,
            'ticker': evidence_bundle.ticker,
            'research_timestamp': evidence_bundle.research_timestamp,
            'content_hash': evidence_bundle.content_hash,
            'reason': freeze_reason,
            'evidence_items_count': len(evidence_bundle.items),
            'total_claims': sum(len(item.claims) for item in evidence_bundle.items)
        }
        
        # Add to manifest evidence log
        if not hasattr(manifest, 'evidence_log'):
            manifest.evidence_log = []
        manifest.evidence_log.append(freeze_entry)


class ReadOnlyEvidenceAccess:
    """Read-only access wrapper for frozen evidence bundles."""
    
    def __init__(self, frozen_evidence: EvidenceBundle):
        """Initialize with frozen evidence bundle."""
        if not frozen_evidence.frozen:
            raise ValueError("ReadOnlyAccess only for frozen evidence")
        
        self._evidence = frozen_evidence
        self._access_log = []
    
    def get_claims_for_citation(self, confidence_threshold: float = 0.80) -> List[Dict[str, Any]]:
        """Get claims formatted for citation by narrative agents."""
        claims = []
        
        for item in self._evidence.items:
            for claim in item.claims:
                if claim.confidence >= confidence_threshold:
                    claims.append({
                        'evidence_id': item.id,
                        'claim_id': f"{item.id}_{len(claims)}",
                        'statement': claim.statement,
                        'driver': claim.driver,
                        'confidence': claim.confidence,
                        'quote': claim.quote,
                        'source_url': item.source_url,
                        'source_title': item.title,
                        'citation_format': f"[ev:{item.id}]"
                    })
        
        self._log_access('get_claims_for_citation', {'threshold': confidence_threshold, 'claims_returned': len(claims)})
        return claims
    
    def get_bundle_metadata(self) -> Dict[str, Any]:
        """Get evidence bundle metadata."""
        metadata = {
            'ticker': self._evidence.ticker,
            'research_timestamp': self._evidence.research_timestamp,
            'freeze_timestamp': self._evidence.freeze_timestamp,
            'total_items': len(self._evidence.items),
            'total_claims': sum(len(item.claims) for item in self._evidence.items),
            'content_hash': self._evidence.content_hash
        }
        
        self._log_access('get_bundle_metadata', metadata)
        return metadata
    
    def search_claims_by_driver(self, driver: str) -> List[Dict[str, Any]]:
        """Search claims by specific driver."""
        matching_claims = []
        
        for item in self._evidence.items:
            for claim in item.claims:
                if claim.driver == driver:
                    matching_claims.append({
                        'evidence_id': item.id,
                        'statement': claim.statement,
                        'confidence': claim.confidence,
                        'magnitude_value': claim.magnitude_value,
                        'magnitude_units': claim.magnitude_units,
                        'quote': claim.quote,
                        'citation_format': f"[ev:{item.id}]"
                    })
        
        self._log_access('search_claims_by_driver', {'driver': driver, 'matches': len(matching_claims)})
        return matching_claims
    
    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get log of all access operations."""
        return self._access_log.copy()
    
    def _log_access(self, operation: str, details: Dict[str, Any]) -> None:
        """Log access operation."""
        self._access_log.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details
        })
    
    def __getattr__(self, name: str) -> Any:
        """Block direct attribute access to prevent modifications."""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        raise AttributeError(f"Read-only access: cannot access '{name}' on frozen evidence")


# Convenience functions
def freeze_evidence_bundle(
    evidence_bundle: EvidenceBundle,
    manifest: Optional[Manifest] = None,
    reason: str = "Research pass completed"
) -> EvidenceBundle:
    """Freeze evidence bundle with default configuration."""
    freezer = EvidenceFreezer()
    return freezer.freeze_evidence_bundle(evidence_bundle, manifest, reason)


def verify_evidence_integrity(evidence_bundle: EvidenceBundle) -> Dict[str, Any]:
    """Verify integrity of evidence bundle."""
    freezer = EvidenceFreezer()
    return freezer.verify_freeze_integrity(evidence_bundle)