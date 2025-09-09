from __future__ import annotations

"""
Comprehensive Snapshot System

Captures every source with complete provenance chain:
source URL → snapshot → evidence claims → driver changes → valuation

Provides integrity verification and corruption detection.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import hashlib
import json
import requests
from urllib.parse import urlparse
import time

from investing_agent.schemas.evidence import SnapshotReference


class SnapshotManager:
    """Manages source content snapshots with integrity verification."""
    
    def __init__(self, snapshot_dir: Path = Path("out/snapshots")):
        """Initialize snapshot manager with storage directory."""
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'InvestingAgent/1.0 (Research Purpose)'
        })
    
    def create_snapshot(
        self,
        url: str,
        content: Optional[str] = None,
        license_info: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SnapshotReference:
        """
        Create snapshot of source content with integrity verification.
        
        Args:
            url: Source URL
            content: Content to snapshot (if None, will fetch from URL)
            license_info: Licensing information
            metadata: Additional metadata
            
        Returns:
            SnapshotReference with integrity information
        """
        # Fetch content if not provided
        if content is None:
            content = self._fetch_content(url)
        
        # Generate content hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Create snapshot reference
        snapshot_ref = SnapshotReference(
            url=url,
            retrieved_at=datetime.now().isoformat(),
            content_sha256=content_hash,
            license_info=license_info or self._detect_license_info(url, content)
        )
        
        # Save snapshot to disk
        snapshot_path = self._save_snapshot(snapshot_ref, content, metadata)
        
        return snapshot_ref
    
    def verify_snapshot_integrity(self, snapshot_ref: SnapshotReference) -> Dict[str, Any]:
        """
        Verify integrity of existing snapshot.
        
        Returns:
            Integrity verification result
        """
        try:
            # Load snapshot content
            snapshot_data = self.load_snapshot(snapshot_ref)
            
            # Recalculate hash
            actual_hash = hashlib.sha256(snapshot_data['content'].encode('utf-8')).hexdigest()
            expected_hash = snapshot_ref.content_sha256
            
            integrity_valid = actual_hash == expected_hash
            
            return {
                'is_valid': integrity_valid,
                'expected_hash': expected_hash,
                'actual_hash': actual_hash,
                'snapshot_exists': True,
                'retrieved_at': snapshot_ref.retrieved_at,
                'verification_time': datetime.now().isoformat(),
                'message': 'Integrity verified' if integrity_valid else 'Hash mismatch detected'
            }
            
        except FileNotFoundError:
            return {
                'is_valid': False,
                'snapshot_exists': False,
                'message': 'Snapshot file not found',
                'verification_time': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'message': f'Verification failed: {str(e)}',
                'verification_time': datetime.now().isoformat()
            }
    
    def load_snapshot(self, snapshot_ref: SnapshotReference) -> Dict[str, Any]:
        """Load snapshot data from storage."""
        snapshot_path = self._get_snapshot_path(snapshot_ref)
        
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")
        
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_provenance_chain(
        self,
        snapshot_refs: List[SnapshotReference],
        ticker: str
    ) -> Dict[str, Any]:
        """
        Create complete provenance chain for evidence sources.
        
        Args:
            snapshot_refs: List of snapshot references
            ticker: Stock ticker
            
        Returns:
            Complete provenance chain documentation
        """
        chain = {
            'ticker': ticker,
            'created_at': datetime.now().isoformat(),
            'total_snapshots': len(snapshot_refs),
            'chain_links': []
        }
        
        for i, snapshot_ref in enumerate(snapshot_refs):
            # Verify each snapshot
            integrity = self.verify_snapshot_integrity(snapshot_ref)
            
            # Load snapshot metadata
            try:
                snapshot_data = self.load_snapshot(snapshot_ref)
                metadata = snapshot_data.get('metadata', {})
            except Exception:
                metadata = {'error': 'Failed to load snapshot'}
            
            chain_link = {
                'link_id': i,
                'snapshot_reference': snapshot_ref.dict(),
                'integrity_status': integrity,
                'metadata': metadata,
                'domain': self._extract_domain(snapshot_ref.url),
                'source_type': self._classify_source_type(snapshot_ref.url)
            }
            
            chain['chain_links'].append(chain_link)
        
        # Calculate chain integrity score
        valid_links = sum(1 for link in chain['chain_links'] if link['integrity_status']['is_valid'])
        chain['integrity_score'] = valid_links / len(snapshot_refs) if snapshot_refs else 0.0
        chain['all_links_valid'] = chain['integrity_score'] == 1.0
        
        return chain
    
    def cleanup_stale_snapshots(self, max_age_days: int = 90) -> Dict[str, Any]:
        """
        Clean up snapshots older than specified age.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Cleanup summary
        """
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        cleaned_files = []
        errors = []
        total_size_freed = 0
        
        for snapshot_file in self.snapshot_dir.rglob("*.json"):
            try:
                # Check file modification time
                if snapshot_file.stat().st_mtime < cutoff_time:
                    file_size = snapshot_file.stat().st_size
                    snapshot_file.unlink()
                    cleaned_files.append(str(snapshot_file))
                    total_size_freed += file_size
            except Exception as e:
                errors.append({'file': str(snapshot_file), 'error': str(e)})
        
        return {
            'cleanup_time': datetime.now().isoformat(),
            'max_age_days': max_age_days,
            'files_cleaned': len(cleaned_files),
            'total_size_freed_bytes': total_size_freed,
            'errors': errors,
            'cleaned_files': cleaned_files[:10]  # First 10 for brevity
        }
    
    def _fetch_content(self, url: str) -> str:
        """Fetch content from URL with error handling."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                # For HTML, try to extract meaningful text
                return self._extract_text_from_html(response.text)
            else:
                return response.text
                
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch content from {url}: {str(e)}")
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract meaningful text from HTML content."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except ImportError:
            # Fallback if BeautifulSoup not available
            return html_content
        except Exception:
            # Fallback on any parsing error
            return html_content
    
    def _detect_license_info(self, url: str, content: str) -> str:
        """Attempt to detect license information from URL and content."""
        domain = self._extract_domain(url)
        
        # Common license patterns
        if 'sec.gov' in domain:
            return 'Public Domain - US Government'
        elif any(news_domain in domain for news_domain in ['reuters.com', 'bloomberg.com', 'wsj.com']):
            return 'Copyright - News Organization'
        elif 'wikipedia.org' in domain:
            return 'Creative Commons'
        else:
            return 'Unknown - Fair Use Research'
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return 'unknown'
    
    def _classify_source_type(self, url: str) -> str:
        """Classify source type based on URL."""
        url_lower = url.lower()
        
        if 'sec.gov' in url_lower:
            if '10-k' in url_lower:
                return '10K'
            elif '10-q' in url_lower:
                return '10Q'
            elif '8-k' in url_lower:
                return '8K'
            else:
                return 'SEC_filing'
        elif any(news in url_lower for news in ['reuters', 'bloomberg', 'wsj', 'cnbc', 'marketwatch']):
            return 'news'
        elif 'earnings' in url_lower and 'transcript' in url_lower:
            return 'transcript'
        elif 'press-release' in url_lower or '/pr/' in url_lower:
            return 'PR'
        else:
            return 'unknown'
    
    def _get_snapshot_path(self, snapshot_ref: SnapshotReference) -> Path:
        """Get file path for snapshot."""
        # Use first 16 characters of hash as filename
        filename = f"snapshot_{snapshot_ref.content_sha256[:16]}.json"
        return self.snapshot_dir / filename
    
    def _save_snapshot(
        self,
        snapshot_ref: SnapshotReference,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Path:
        """Save snapshot to disk."""
        snapshot_path = self._get_snapshot_path(snapshot_ref)
        
        snapshot_data = {
            'snapshot_reference': snapshot_ref.dict(),
            'content': content,
            'metadata': metadata or {},
            'saved_at': datetime.now().isoformat(),
            'content_length': len(content),
            'domain': self._extract_domain(snapshot_ref.url),
            'source_type': self._classify_source_type(snapshot_ref.url)
        }
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
        
        return snapshot_path
    
    def get_snapshot_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored snapshots."""
        snapshot_files = list(self.snapshot_dir.rglob("*.json"))
        
        total_size = sum(f.stat().st_size for f in snapshot_files)
        
        # Analyze by source type
        source_types = {}
        domains = set()
        
        for snapshot_file in snapshot_files[:100]:  # Sample first 100 to avoid performance issues
            try:
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
                    
                source_type = data.get('source_type', 'unknown')
                domain = data.get('domain', 'unknown')
                
                source_types[source_type] = source_types.get(source_type, 0) + 1
                domains.add(domain)
                
            except Exception:
                continue
        
        return {
            'total_snapshots': len(snapshot_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'unique_domains': len(domains),
            'source_type_breakdown': source_types,
            'snapshot_directory': str(self.snapshot_dir),
            'statistics_generated_at': datetime.now().isoformat()
        }


# Convenience functions
def create_source_snapshot(
    url: str,
    content: Optional[str] = None,
    snapshot_dir: Path = Path("out/snapshots")
) -> SnapshotReference:
    """Create snapshot with default configuration."""
    manager = SnapshotManager(snapshot_dir)
    return manager.create_snapshot(url, content)


def verify_snapshot(
    snapshot_ref: SnapshotReference,
    snapshot_dir: Path = Path("out/snapshots")
) -> Dict[str, Any]:
    """Verify snapshot integrity with default configuration."""
    manager = SnapshotManager(snapshot_dir)
    return manager.verify_snapshot_integrity(snapshot_ref)