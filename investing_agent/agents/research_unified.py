from __future__ import annotations

"""
Unified Research Agent for Evidence-Based Valuation

Merges news.py and research_llm.py into single three-phase processor:
1. Headline analysis - filter for valuation relevance  
2. Materiality assessment - assess driver impact potential
3. Full extraction - extract claims with confidence scoring

Designed for "research-once-then-freeze" evidence pipeline.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib
import json
from pathlib import Path

from investing_agent.schemas.evidence import EvidenceBundle, EvidenceItem, EvidenceClaim, SnapshotReference
from investing_agent.schemas.inputs import InputsI
from investing_agent.llm.enhanced_provider import get_provider
from investing_agent.connectors.news import search_news as fetch_news


class ResearchUnified:
    """Unified research agent with three-phase evidence extraction."""
    
    def __init__(self, confidence_threshold: float = 0.80):
        """Initialize research agent with configuration."""
        self.confidence_threshold = confidence_threshold
        self.llm_provider = get_provider()
        
    def execute_research_pass(
        self, 
        ticker: str, 
        inputs: Optional[InputsI] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        cassette_path: Optional[str] = None
    ) -> EvidenceBundle:
        """
        Execute complete research pass generating evidence bundle.
        
        Args:
            ticker: Stock ticker symbol
            inputs: Current InputsI for context (optional)
            sources: External sources to analyze (optional)
            cassette_path: Path for deterministic testing (optional)
            
        Returns:
            Complete evidence bundle with extracted claims
        """
        # Initialize evidence bundle
        evidence_bundle = EvidenceBundle(
            research_timestamp=datetime.now().isoformat(),
            ticker=ticker
        )
        
        # Determine sources to analyze
        if sources is None:
            sources = self._fetch_default_sources(ticker)
        
        # Process each source through three-phase pipeline
        for source in sources:
            try:
                evidence_item = self._process_source_three_phase(source, ticker, cassette_path)
                if evidence_item and evidence_item.claims:
                    evidence_bundle.items.append(evidence_item)
            except Exception as e:
                # Log error but continue with other sources
                print(f"Warning: Failed to process source {source.get('url', 'unknown')}: {str(e)}")
        
        return evidence_bundle
    
    def _fetch_default_sources(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch default news and filing sources for ticker."""
        sources = []
        
        # Fetch recent news
        try:
            news_bundle = fetch_news(ticker, limit=10)  
            for news_item in news_bundle.items:
                sources.append({
                    'url': news_item.url,
                    'title': news_item.title,
                    'snippet': news_item.snippet,
                    'date': news_item.date,
                    'source_type': 'news',
                    'content': getattr(news_item, 'content', None)
                })
        except Exception as e:
            print(f"Warning: Failed to fetch news for {ticker}: {str(e)}")
        
        # TODO: Add SEC filing sources (10K, 10Q, 8K)
        # TODO: Add earnings transcript sources
        
        return sources
    
    def _process_source_three_phase(
        self, 
        source: Dict[str, Any], 
        ticker: str,
        cassette_path: Optional[str] = None
    ) -> Optional[EvidenceItem]:
        """Process single source through three-phase analysis."""
        
        # Phase 1: Headline Analysis - Filter for valuation relevance
        phase1_result = self._phase1_headline_analysis(source)
        if not phase1_result['is_relevant']:
            return None  # Early exit for non-material content
        
        # Phase 2: Materiality Assessment - Assess driver impact potential
        phase2_result = self._phase2_materiality_assessment(source, phase1_result)
        if not phase2_result['is_material']:
            return None  # Early exit for non-material content
        
        # Phase 3: Full Extraction - Extract specific claims with confidence
        phase3_result = self._phase3_full_extraction(source, phase2_result, cassette_path)
        
        # Create evidence item if we have claims
        if phase3_result['claims']:
            # Create snapshot reference
            snapshot_ref = self._create_snapshot(source)
            
            evidence_item = EvidenceItem(
                id=f"ev_{hashlib.md5(source['url'].encode()).hexdigest()[:8]}",
                source_url=source['url'],
                snapshot_id=snapshot_ref['snapshot_id'],
                date=source.get('date'),
                source_type=source.get('source_type', 'news'),
                title=source.get('title', ''),
                claims=phase3_result['claims']
            )
            
            return evidence_item
        
        return None
    
    def _phase1_headline_analysis(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Quick relevance filtering based on headline."""
        title = source.get('title', '')
        snippet = source.get('snippet', '')
        
        # Heuristic relevance scoring
        relevance_indicators = [
            'guidance', 'outlook', 'forecast', 'expects', 'projects',
            'revenue', 'sales', 'margin', 'profit', 'earnings',
            'growth', 'expansion', 'investment', 'capex',
            'market share', 'competition', 'regulatory',
            'product launch', 'partnership', 'acquisition'
        ]
        
        text = (title + ' ' + snippet).lower()
        relevance_score = sum(1 for indicator in relevance_indicators if indicator in text)
        
        # Simple threshold-based filtering
        is_relevant = relevance_score >= 2 or any(key in text for key in ['guidance', 'outlook', 'earnings'])
        
        return {
            'is_relevant': is_relevant,
            'relevance_score': relevance_score,
            'reasoning': f"Found {relevance_score} relevance indicators"
        }
    
    def _phase2_materiality_assessment(
        self, 
        source: Dict[str, Any], 
        phase1_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 2: Assess materiality and potential driver impact."""
        title = source.get('title', '')
        snippet = source.get('snippet', '')
        
        # Look for quantitative indicators
        has_numbers = any(char.isdigit() for char in title + snippet)
        
        # Look for driver-specific keywords
        driver_keywords = {
            'growth': ['growth', 'revenue', 'sales', 'expansion', 'increase'],
            'margin': ['margin', 'profit', 'cost', 'efficiency', 'productivity'],
            'wacc': ['interest', 'debt', 'financing', 'rate', 'cost of capital'],
            's2c': ['capex', 'investment', 'capacity', 'assets', 'efficiency']
        }
        
        text = (title + snippet).lower()
        potential_drivers = []
        for driver, keywords in driver_keywords.items():
            if any(keyword in text for keyword in keywords):
                potential_drivers.append(driver)
        
        # Materiality scoring
        materiality_score = 0
        if has_numbers:
            materiality_score += 2
        materiality_score += len(potential_drivers)
        materiality_score += phase1_result['relevance_score'] * 0.5
        
        is_material = materiality_score >= 3.0
        
        return {
            'is_material': is_material,
            'materiality_score': materiality_score,
            'potential_drivers': potential_drivers,
            'has_numbers': has_numbers,
            'reasoning': f"Materiality score {materiality_score:.1f}, drivers: {potential_drivers}"
        }
    
    def _phase3_full_extraction(
        self,
        source: Dict[str, Any],
        phase2_result: Dict[str, Any],
        cassette_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Phase 3: Full content analysis with LLM-based claim extraction."""
        
        # Prepare content for LLM analysis
        content = source.get('content', '') or (source.get('title', '') + '. ' + source.get('snippet', ''))
        
        # Build extraction prompt
        prompt = self._build_extraction_prompt(
            content=content,
            ticker=source.get('ticker', 'UNKNOWN'),
            potential_drivers=phase2_result.get('potential_drivers', []),
            source_type=source.get('source_type', 'news')
        )
        
        messages = [
            {"role": "system", "content": "You are a professional equity research analyst extracting valuation-relevant claims from sources."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Call LLM with deterministic parameters
            response = self.llm_provider.call(
                model_name="research-premium",
                messages=messages,
                params={
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "seed": 2025
                },
                cassette_path=cassette_path
            )
            
            # Parse LLM response into structured claims
            claims = self._parse_llm_claims_response(response["choices"][0]["message"]["content"])
            
            # Filter by confidence threshold
            high_confidence_claims = [
                claim for claim in claims 
                if claim.confidence >= self.confidence_threshold
            ]
            
            return {
                'claims': high_confidence_claims,
                'total_extracted': len(claims),
                'high_confidence': len(high_confidence_claims),
                'llm_response': response["choices"][0]["message"]["content"]
            }
            
        except Exception as e:
            print(f"Warning: LLM extraction failed for {source.get('url', 'unknown')}: {str(e)}")
            return {'claims': [], 'total_extracted': 0, 'high_confidence': 0}
    
    def _build_extraction_prompt(
        self,
        content: str,
        ticker: str,
        potential_drivers: List[str],
        source_type: str
    ) -> str:
        """Build comprehensive extraction prompt for LLM."""
        return f"""
Extract valuation-relevant claims from this {source_type} content for {ticker}.

Content:
{content[:2000]}  # Truncate for token limits

Focus on these valuation drivers: {', '.join(potential_drivers) if potential_drivers else 'growth, margin, wacc, s2c'}

For each claim, provide:
1. Driver affected (growth/margin/wacc/s2c)
2. Direction of impact (+/-)
3. Magnitude if quantified (number + units: %/bps/abs)
4. Time horizon (y1/y2-3/LT)
5. Confidence score (0.0-1.0)
6. Supporting quote from text
7. Clear statement of the claim

Return as JSON array with format:
[
  {{
    "driver": "growth",
    "statement": "Management raised FY25 revenue guidance to 15-20% growth",
    "direction": "+",
    "magnitude_value": 17.5,
    "magnitude_units": "%", 
    "horizon": "y1",
    "confidence": 0.90,
    "quote": "We now expect revenue growth of 15-20% in 2025"
  }}
]

Only include claims with confidence ≥ 0.70. Return empty array if no relevant claims found.
"""
    
    def _parse_llm_claims_response(self, llm_response: str) -> List[EvidenceClaim]:
        """Parse LLM response into structured EvidenceClaim objects."""
        claims = []
        
        try:
            # Extract JSON from response
            json_start = llm_response.find('[')
            json_end = llm_response.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                claims_data = json.loads(llm_response[json_start:json_end])
                
                for claim_data in claims_data:
                    try:
                        claim = EvidenceClaim(
                            driver=claim_data['driver'],
                            statement=claim_data['statement'],
                            direction=claim_data['direction'],
                            magnitude_units=claim_data.get('magnitude_units', '%'),
                            magnitude_value=claim_data.get('magnitude_value'),
                            horizon=claim_data['horizon'],
                            confidence=claim_data['confidence'],
                            quote=claim_data['quote']
                        )
                        claims.append(claim)
                        
                    except Exception as e:
                        print(f"Warning: Failed to parse claim: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Warning: Failed to parse LLM response: {str(e)}")
        
        return claims
    
    def _create_snapshot(self, source: Dict[str, Any]) -> Dict[str, str]:
        """Create snapshot reference for source content."""
        # Generate snapshot ID
        content = source.get('content', '') or (source.get('title', '') + '. ' + source.get('snippet', ''))
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        snapshot_id = f"snap_{content_hash[:12]}"
        
        return {
            'snapshot_id': snapshot_id,
            'content_hash': content_hash
        }
        
    def freeze_evidence(self, evidence_bundle: EvidenceBundle) -> EvidenceBundle:
        """Mark evidence bundle as frozen (immutable)."""
        evidence_bundle.freeze()
        return evidence_bundle


# Convenience functions for backward compatibility
def generate_evidence_bundle(
    ticker: str,
    inputs: Optional[InputsI] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    cassette_path: Optional[str] = None,
    confidence_threshold: float = 0.80
) -> EvidenceBundle:
    """Generate evidence bundle using unified research agent."""
    agent = ResearchUnified(confidence_threshold=confidence_threshold)
    return agent.execute_research_pass(ticker, inputs, sources, cassette_path)


def freeze_evidence_bundle(evidence_bundle: EvidenceBundle) -> EvidenceBundle:
    """Freeze evidence bundle to prevent modifications."""
    evidence_bundle.freeze()
    return evidence_bundle