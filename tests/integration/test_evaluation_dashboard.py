"""Integration tests for evaluation dashboard and continuous improvement system."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import json

from investing_agent.schemas.evaluation_metrics import (
    EvaluationConfig,
    EvaluationResult,
    EvaluationScore,
    HardMetrics,
    EvaluationDimension,
)
from investing_agent.storage.metrics_storage import MetricsStorage
from investing_agent.evaluation.evaluation_runner import EvaluationRunner
from investing_agent.evaluation.trend_analyzer import TrendAnalyzer
from investing_agent.evaluation.recommendation_engine import RecommendationEngine
from investing_agent.evaluation.dashboard import EvaluationDashboard


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        yield Path(f.name)


@pytest.fixture
def sample_evaluation():
    """Create sample evaluation result."""
    return EvaluationResult(
        evaluation_id="eval_test_001",
        report_id="report_test_001",
        ticker="TEST",
        company="Test Corporation",
        report_timestamp=datetime.utcnow(),
        evaluation_timestamp=datetime.utcnow(),
        dimensional_scores=[
            EvaluationScore(
                dimension=EvaluationDimension.STRATEGIC_NARRATIVE,
                score=7.5,
                percentage=75,
                details="Good strategic narrative"
            ),
            EvaluationScore(
                dimension=EvaluationDimension.ANALYTICAL_RIGOR,
                score=8.0,
                percentage=80,
                details="Strong analytical depth"
            ),
            EvaluationScore(
                dimension=EvaluationDimension.INDUSTRY_CONTEXT,
                score=6.5,
                percentage=65,
                details="Adequate industry analysis"
            ),
            EvaluationScore(
                dimension=EvaluationDimension.PROFESSIONAL_PRESENTATION,
                score=7.0,
                percentage=70,
                details="Good presentation"
            ),
            EvaluationScore(
                dimension=EvaluationDimension.CITATION_DISCIPLINE,
                score=8.5,
                percentage=85,
                details="Excellent citations"
            ),
        ],
        hard_metrics=HardMetrics(
            evidence_coverage=0.85,
            citation_density=0.75,
            contradiction_rate=0.15,
            fixture_stability=True,
            numeric_accuracy=0.95
        ),
        recommendations=[
            "Enhance industry context analysis",
            "Add more competitive positioning details"
        ]
    )


class TestMetricsStorage:
    """Test metrics storage system."""
    
    def test_storage_initialization(self, temp_db):
        """Test storage initialization."""
        storage = MetricsStorage(db_path=temp_db)
        assert temp_db.exists()
    
    def test_save_and_retrieve_evaluation(self, temp_db, sample_evaluation):
        """Test saving and retrieving evaluation."""
        storage = MetricsStorage(db_path=temp_db)
        
        # Save evaluation
        success = storage.save_evaluation(sample_evaluation)
        assert success
        
        # Retrieve evaluation
        retrieved = storage.get_evaluation(sample_evaluation.evaluation_id)
        assert retrieved is not None
        assert retrieved.ticker == "TEST"
        assert retrieved.overall_score == sample_evaluation.overall_score
    
    def test_ticker_history(self, temp_db, sample_evaluation):
        """Test ticker history retrieval."""
        storage = MetricsStorage(db_path=temp_db)
        
        # Save multiple evaluations
        for i in range(3):
            eval_copy = sample_evaluation.model_copy()
            eval_copy.evaluation_id = f"eval_test_{i:03d}"
            eval_copy.overall_score = 7.0 + i * 0.5
            storage.save_evaluation(eval_copy)
        
        # Get history
        history = storage.get_ticker_history("TEST")
        assert len(history.evaluations) == 3
        assert history.average_score > 0
        assert history.latest_evaluation is not None
    
    def test_summary_generation(self, temp_db, sample_evaluation):
        """Test summary generation."""
        storage = MetricsStorage(db_path=temp_db)
        storage.save_evaluation(sample_evaluation)
        
        summary = storage.generate_summary()
        assert summary.total_evaluations == 1
        assert summary.average_score > 0


class TestEvaluationRunner:
    """Test evaluation runner."""
    
    def test_hard_metrics_calculation(self):
        """Test hard metrics calculation."""
        runner = EvaluationRunner()
        
        report_content = """
        # Investment Report
        
        The company shows strong growth [ev:001] with revenue increasing.
        Operating margins are improving [ev:002] driven by efficiency gains.
        
        Management expects continued growth [ev:003] in the coming years.
        The competitive position remains strong [ref:computed:valuation.value].
        """
        
        metrics = runner._calculate_hard_metrics(report_content)
        assert metrics.evidence_coverage > 0
        assert metrics.citation_density > 0
        assert metrics.contradiction_rate >= 0
    
    def test_recommendation_generation(self):
        """Test recommendation generation."""
        runner = EvaluationRunner()
        
        dimensional_scores = [
            EvaluationScore(
                dimension=EvaluationDimension.STRATEGIC_NARRATIVE,
                score=5.0,
                percentage=50
            ),
            EvaluationScore(
                dimension=EvaluationDimension.ANALYTICAL_RIGOR,
                score=8.0,
                percentage=80
            ),
        ]
        
        hard_metrics = HardMetrics(
            evidence_coverage=0.60,
            citation_density=0.50,
            contradiction_rate=0.10,
            fixture_stability=True
        )
        
        recommendations = runner._generate_recommendations(dimensional_scores, hard_metrics)
        assert len(recommendations) > 0
        assert any("narrative" in r.lower() for r in recommendations)
        assert any("evidence" in r.lower() for r in recommendations)


class TestTrendAnalyzer:
    """Test trend analyzer."""
    
    def test_trend_analysis(self, temp_db):
        """Test trend analysis."""
        storage = MetricsStorage(db_path=temp_db)
        analyzer = TrendAnalyzer(storage)
        
        # Create evaluation history
        for i in range(5):
            eval = EvaluationResult(
                evaluation_id=f"eval_{i:03d}",
                report_id=f"report_{i:03d}",
                ticker="TREND",
                company="Trend Corp",
                report_timestamp=datetime.utcnow() - timedelta(days=5-i),
                evaluation_timestamp=datetime.utcnow() - timedelta(days=5-i),
                dimensional_scores=[
                    EvaluationScore(
                        dimension=EvaluationDimension.STRATEGIC_NARRATIVE,
                        score=6.0 + i * 0.5,
                        percentage=60 + i * 5
                    )
                ],
                hard_metrics=HardMetrics(
                    evidence_coverage=0.80,
                    citation_density=0.70,
                    contradiction_rate=0.15,
                    fixture_stability=True
                )
            )
            storage.save_evaluation(eval)
        
        # Analyze trends
        trends = analyzer.analyze_ticker_trends("TREND")
        assert trends["ticker"] == "TREND"
        assert trends["trend"] is not None
        assert trends["improvement_percentage"] > 0
    
    def test_pattern_identification(self, temp_db):
        """Test pattern identification."""
        storage = MetricsStorage(db_path=temp_db)
        analyzer = TrendAnalyzer(storage)
        
        # Create volatile history
        scores = [7.0, 8.5, 6.0, 9.0, 5.5]
        for i, score in enumerate(scores):
            eval = EvaluationResult(
                evaluation_id=f"eval_{i:03d}",
                report_id=f"report_{i:03d}",
                ticker="VOLATILE",
                company="Volatile Corp",
                report_timestamp=datetime.utcnow() - timedelta(days=len(scores)-i),
                evaluation_timestamp=datetime.utcnow() - timedelta(days=len(scores)-i),
                dimensional_scores=[
                    EvaluationScore(
                        dimension=EvaluationDimension.STRATEGIC_NARRATIVE,
                        score=score,
                        percentage=score * 10
                    )
                ],
                hard_metrics=HardMetrics(
                    evidence_coverage=0.80,
                    citation_density=0.70,
                    contradiction_rate=0.15,
                    fixture_stability=True
                )
            )
            eval.overall_score = score  # Override calculation
            storage.save_evaluation(eval)
        
        patterns = analyzer.identify_patterns("VOLATILE")
        assert "patterns" in patterns
        assert patterns["score_volatility"] > 1.0


class TestRecommendationEngine:
    """Test recommendation engine."""
    
    def test_recommendation_generation(self, sample_evaluation):
        """Test recommendation generation."""
        engine = RecommendationEngine()
        
        recommendations = engine.generate_recommendations(sample_evaluation)
        assert len(recommendations) > 0
        
        # Check for low-scoring dimension recommendations
        low_score_dims = [s for s in sample_evaluation.dimensional_scores if s.score < 7.0]
        if low_score_dims:
            assert any(r.category in [d.dimension for d in low_score_dims] for r in recommendations)
    
    def test_implementation_roadmap(self, temp_db, sample_evaluation):
        """Test implementation roadmap generation."""
        storage = MetricsStorage(db_path=temp_db)
        engine = RecommendationEngine(storage)
        
        storage.save_evaluation(sample_evaluation)
        
        roadmap = engine.get_implementation_roadmap("TEST")
        assert roadmap["ticker"] == "TEST"
        assert "current_score" in roadmap
        assert "projected_score" in roadmap
        assert "recommendations_by_priority" in roadmap


class TestEvaluationDashboard:
    """Test evaluation dashboard."""
    
    def test_dashboard_initialization(self, temp_db):
        """Test dashboard initialization."""
        storage = MetricsStorage(db_path=temp_db)
        dashboard = EvaluationDashboard(storage=storage)
        
        assert dashboard.storage is not None
        assert dashboard.runner is not None
        assert dashboard.trend_analyzer is not None
        assert dashboard.recommendation_engine is not None
    
    def test_html_generation(self, temp_db, sample_evaluation):
        """Test HTML dashboard generation."""
        storage = MetricsStorage(db_path=temp_db)
        storage.save_evaluation(sample_evaluation)
        
        dashboard = EvaluationDashboard(storage=storage)
        html = dashboard.generate_dashboard_html()
        
        assert "<html" in html
        assert "Report Quality Evaluation Dashboard" in html
        assert "TEST" in html
        assert "Test Corporation" in html
    
    def test_ticker_report_generation(self, temp_db, sample_evaluation):
        """Test ticker report generation."""
        storage = MetricsStorage(db_path=temp_db)
        storage.save_evaluation(sample_evaluation)
        
        dashboard = EvaluationDashboard(storage=storage)
        report = dashboard.generate_ticker_report("TEST")
        
        assert report["ticker"] == "TEST"
        assert "latest_evaluation" in report
        assert "trends" in report
        assert "recommendations" in report
        assert "roadmap" in report
    
    def test_batch_evaluation(self, temp_db):
        """Test batch evaluation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir)
            
            # Create sample reports
            for ticker in ["TEST1", "TEST2", "TEST3"]:
                report_path = report_dir / f"{ticker}_report.md"
                report_path.write_text(f"""
                # {ticker} Investment Report
                
                Strong growth prospects [ev:001] with improving margins [ev:002].
                Competitive position remains solid [ref:computed:valuation.value].
                """)
            
            storage = MetricsStorage(db_path=temp_db)
            dashboard = EvaluationDashboard(storage=storage)
            
            # Mock LLM evaluation
            dashboard.runner._evaluate_single_dimension = lambda *args: (7.0, "Good")
            
            results = dashboard.run_batch_evaluation(report_dir)
            
            assert "batch_id" in results
            assert results["total_evaluated"] == 3
            assert "average_score" in results
    
    def test_metrics_export(self, temp_db, sample_evaluation):
        """Test metrics export."""
        storage = MetricsStorage(db_path=temp_db)
        storage.save_evaluation(sample_evaluation)
        
        dashboard = EvaluationDashboard(storage=storage)
        
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            export_path = Path(f.name)
            success = dashboard.export_metrics(export_path)
            
            assert success
            assert export_path.exists()
            
            # Verify export content
            with export_path.open() as file:
                data = json.load(file)
                assert "evaluations" in data
                assert len(data["evaluations"]) == 1


if __name__ == "__main__":
    pytest.main([__file__])