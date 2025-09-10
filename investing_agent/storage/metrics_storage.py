"""Metrics storage system for evaluation results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from investing_agent.schemas.evaluation_metrics import (
    EvaluationResult,
    EvaluationHistory,
    EvaluationSummary,
    EvaluationBatch,
    EvaluationDimension,
    DimensionalAnalysis,
    QualityTrend,
)


class MetricsStorage:
    """Storage system for evaluation metrics using SQLite."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize metrics storage.
        
        Args:
            db_path: Path to SQLite database file (defaults to out/metrics.db)
        """
        if db_path is None:
            db_path = Path("out") / "metrics.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create evaluations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    company TEXT NOT NULL,
                    report_timestamp TIMESTAMP,
                    evaluation_timestamp TIMESTAMP,
                    overall_score REAL,
                    overall_percentage REAL,
                    passes_quality_gates BOOLEAN,
                    data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create dimensional scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dimensional_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluation_id TEXT,
                    dimension TEXT,
                    score REAL,
                    percentage REAL,
                    details TEXT,
                    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id)
                )
            """)
            
            # Create hard metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hard_metrics (
                    evaluation_id TEXT PRIMARY KEY,
                    evidence_coverage REAL,
                    citation_density REAL,
                    contradiction_rate REAL,
                    fixture_stability BOOLEAN,
                    numeric_accuracy REAL,
                    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id)
                )
            """)
            
            # Create recommendations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluation_id TEXT,
                    recommendation TEXT,
                    priority INTEGER,
                    category TEXT,
                    FOREIGN KEY (evaluation_id) REFERENCES evaluations(evaluation_id)
                )
            """)
            
            # Create batches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    batch_timestamp TIMESTAMP,
                    total_evaluations INTEGER,
                    average_score REAL,
                    passing_rate REAL,
                    processing_time REAL,
                    total_cost REAL,
                    config JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON evaluations(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON evaluations(evaluation_timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_score ON evaluations(overall_score)")
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_evaluation(self, evaluation: EvaluationResult) -> bool:
        """Save evaluation result to storage.
        
        Args:
            evaluation: Evaluation result to save
            
        Returns:
            Success status
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Save main evaluation
                cursor.execute("""
                    INSERT OR REPLACE INTO evaluations 
                    (evaluation_id, report_id, ticker, company, report_timestamp, 
                     evaluation_timestamp, overall_score, overall_percentage, 
                     passes_quality_gates, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    evaluation.evaluation_id,
                    evaluation.report_id,
                    evaluation.ticker,
                    evaluation.company,
                    evaluation.report_timestamp.isoformat(),
                    evaluation.evaluation_timestamp.isoformat(),
                    evaluation.overall_score,
                    evaluation.overall_percentage,
                    evaluation.passes_quality_gates,
                    evaluation.model_dump_json()
                ))
                
                # Save dimensional scores
                for score in evaluation.dimensional_scores:
                    cursor.execute("""
                        INSERT INTO dimensional_scores 
                        (evaluation_id, dimension, score, percentage, details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        evaluation.evaluation_id,
                        score.dimension.value,
                        score.score,
                        score.percentage,
                        score.details
                    ))
                
                # Save hard metrics
                cursor.execute("""
                    INSERT OR REPLACE INTO hard_metrics 
                    (evaluation_id, evidence_coverage, citation_density, 
                     contradiction_rate, fixture_stability, numeric_accuracy)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    evaluation.evaluation_id,
                    evaluation.hard_metrics.evidence_coverage,
                    evaluation.hard_metrics.citation_density,
                    evaluation.hard_metrics.contradiction_rate,
                    evaluation.hard_metrics.fixture_stability,
                    evaluation.hard_metrics.numeric_accuracy
                ))
                
                # Save recommendations
                for rec in evaluation.recommendations:
                    cursor.execute("""
                        INSERT INTO recommendations 
                        (evaluation_id, recommendation, priority, category)
                        VALUES (?, ?, ?, ?)
                    """, (
                        evaluation.evaluation_id,
                        rec,
                        1,  # Default priority
                        "general"
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving evaluation: {e}")
            return False
    
    def get_evaluation(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Get evaluation by ID.
        
        Args:
            evaluation_id: Evaluation ID
            
        Returns:
            Evaluation result or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM evaluations WHERE evaluation_id = ?
            """, (evaluation_id,))
            
            row = cursor.fetchone()
            if row:
                return EvaluationResult.model_validate_json(row["data"])
            return None
    
    def get_ticker_history(self, ticker: str, limit: int = 100) -> EvaluationHistory:
        """Get evaluation history for a ticker.
        
        Args:
            ticker: Company ticker
            limit: Maximum number of evaluations to retrieve
            
        Returns:
            Evaluation history
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data, company FROM evaluations 
                WHERE ticker = ? 
                ORDER BY evaluation_timestamp DESC 
                LIMIT ?
            """, (ticker, limit))
            
            rows = cursor.fetchall()
            
            if not rows:
                return EvaluationHistory(ticker=ticker, company="Unknown", evaluations=[])
            
            evaluations = [EvaluationResult.model_validate_json(row["data"]) for row in rows]
            company = rows[0]["company"] if rows else "Unknown"
            
            return EvaluationHistory(
                ticker=ticker,
                company=company,
                evaluations=evaluations
            )
    
    def get_recent_evaluations(self, days: int = 7, limit: int = 100) -> List[EvaluationResult]:
        """Get recent evaluations.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of evaluations
            
        Returns:
            List of recent evaluations
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM evaluations 
                WHERE evaluation_timestamp >= ? 
                ORDER BY evaluation_timestamp DESC 
                LIMIT ?
            """, (cutoff, limit))
            
            rows = cursor.fetchall()
            return [EvaluationResult.model_validate_json(row["data"]) for row in rows]
    
    def get_top_performers(self, limit: int = 10) -> List[EvaluationResult]:
        """Get top performing evaluations.
        
        Args:
            limit: Number of top performers
            
        Returns:
            List of top evaluations
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM evaluations 
                WHERE passes_quality_gates = 1 
                ORDER BY overall_score DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [EvaluationResult.model_validate_json(row["data"]) for row in rows]
    
    def get_dimensional_analysis(self, ticker: str) -> Dict[EvaluationDimension, DimensionalAnalysis]:
        """Get dimensional analysis for a ticker.
        
        Args:
            ticker: Company ticker
            
        Returns:
            Dimensional analysis by dimension
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get dimensional scores
            cursor.execute("""
                SELECT ds.dimension, ds.score
                FROM dimensional_scores ds
                JOIN evaluations e ON ds.evaluation_id = e.evaluation_id
                WHERE e.ticker = ?
                ORDER BY e.evaluation_timestamp DESC
            """, (ticker,))
            
            rows = cursor.fetchall()
            
            # Group by dimension
            dimension_data = {}
            for row in rows:
                dim = EvaluationDimension(row["dimension"])
                if dim not in dimension_data:
                    dimension_data[dim] = []
                dimension_data[dim].append(row["score"])
            
            # Create analysis
            analyses = {}
            for dim, scores in dimension_data.items():
                if scores:
                    analyses[dim] = DimensionalAnalysis(
                        dimension=dim,
                        current_score=scores[0],
                        historical_scores=scores[:10]  # Last 10 scores
                    )
            
            return analyses
    
    def generate_summary(self) -> EvaluationSummary:
        """Generate overall summary statistics.
        
        Returns:
            Summary statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get overall statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(overall_score) as avg_score,
                    MAX(overall_score) as max_score,
                    MIN(overall_score) as min_score,
                    SUM(CASE WHEN passes_quality_gates = 1 THEN 1 ELSE 0 END) as passing
                FROM evaluations
            """)
            
            row = cursor.fetchone()
            
            summary = EvaluationSummary()
            if row and row["total"] > 0:
                summary.total_evaluations = row["total"]
                summary.average_score = row["avg_score"] or 0.0
                summary.highest_score = row["max_score"] or 0.0
                summary.lowest_score = row["min_score"] or 10.0
                summary.passing_rate = (row["passing"] / row["total"]) * 100
            
            # Get top performers
            cursor.execute("""
                SELECT DISTINCT ticker FROM evaluations 
                WHERE overall_score >= 8.0 
                ORDER BY overall_score DESC 
                LIMIT 5
            """)
            summary.top_performers = [row["ticker"] for row in cursor.fetchall()]
            
            # Get needs attention
            cursor.execute("""
                SELECT DISTINCT ticker FROM evaluations 
                WHERE overall_score < 6.0 
                ORDER BY overall_score ASC 
                LIMIT 5
            """)
            summary.needs_attention = [row["ticker"] for row in cursor.fetchall()]
            
            return summary
    
    def save_batch(self, batch: EvaluationBatch) -> bool:
        """Save batch evaluation results.
        
        Args:
            batch: Batch evaluation results
            
        Returns:
            Success status
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Save batch metadata
                cursor.execute("""
                    INSERT INTO batches 
                    (batch_id, batch_timestamp, total_evaluations, average_score, 
                     passing_rate, processing_time, total_cost, config)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    batch.batch_id,
                    batch.batch_timestamp.isoformat(),
                    batch.summary.total_evaluations,
                    batch.summary.average_score,
                    batch.summary.passing_rate,
                    batch.processing_time_seconds,
                    batch.total_cost_usd,
                    batch.config.model_dump_json()
                ))
                
                # Save individual evaluations
                for evaluation in batch.evaluations:
                    self.save_evaluation(evaluation)
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving batch: {e}")
            return False
    
    def export_to_json(self, output_path: Path) -> bool:
        """Export all data to JSON file.
        
        Args:
            output_path: Output file path
            
        Returns:
            Success status
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT data FROM evaluations ORDER BY evaluation_timestamp DESC")
                evaluations = [json.loads(row["data"]) for row in cursor.fetchall()]
                
                export_data = {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "total_evaluations": len(evaluations),
                    "evaluations": evaluations
                }
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("w") as f:
                    json.dump(export_data, f, indent=2)
                
                return True
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False