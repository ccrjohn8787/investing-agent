"""Evaluation dashboard for report quality monitoring."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from investing_agent.schemas.evaluation_metrics import (
    EvaluationConfig,
    EvaluationSummary,
)
from investing_agent.storage.metrics_storage import MetricsStorage
from investing_agent.evaluation.evaluation_runner import EvaluationRunner
from investing_agent.evaluation.trend_analyzer import TrendAnalyzer
from investing_agent.evaluation.recommendation_engine import RecommendationEngine


class EvaluationDashboard:
    """Dashboard for monitoring and improving report quality."""
    
    def __init__(
        self,
        storage: Optional[MetricsStorage] = None,
        config: Optional[EvaluationConfig] = None
    ):
        """Initialize evaluation dashboard.
        
        Args:
            storage: Metrics storage instance
            config: Evaluation configuration
        """
        self.storage = storage or MetricsStorage()
        self.config = config or EvaluationConfig()
        
        # Initialize components
        self.runner = EvaluationRunner(config, storage)
        self.trend_analyzer = TrendAnalyzer(storage)
        self.recommendation_engine = RecommendationEngine(storage)
    
    def generate_dashboard_html(self, output_path: Optional[Path] = None) -> str:
        """Generate HTML dashboard.
        
        Args:
            output_path: Optional path to save HTML
            
        Returns:
            HTML content
        """
        # Get summary data
        summary = self.storage.generate_summary()
        recent_evaluations = self.storage.get_recent_evaluations(days=7)
        top_performers = self.storage.get_top_performers(limit=5)
        
        # Generate HTML
        html = self._generate_html_template(summary, recent_evaluations, top_performers)
        
        # Save if requested
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html)
        
        return html
    
    def _generate_html_template(
        self,
        summary: EvaluationSummary,
        recent_evaluations: List,
        top_performers: List
    ) -> str:
        """Generate HTML template for dashboard.
        
        Args:
            summary: Overall summary
            recent_evaluations: Recent evaluations
            top_performers: Top performing reports
            
        Returns:
            HTML content
        """
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Quality Evaluation Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            margin-bottom: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2563eb;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        h2 {{
            color: #333;
            margin-bottom: 20px;
            border-bottom: 2px solid #e5e5e5;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e5e5;
        }}
        th {{
            background: #f9fafb;
            font-weight: 600;
            color: #333;
        }}
        .score {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}
        .score-excellent {{ background: #10b981; color: white; }}
        .score-good {{ background: #f59e0b; color: white; }}
        .score-poor {{ background: #ef4444; color: white; }}
        .status-passing {{ color: #10b981; font-weight: 600; }}
        .status-failing {{ color: #ef4444; font-weight: 600; }}
        .trend-improving {{ color: #10b981; }}
        .trend-stable {{ color: #6b7280; }}
        .trend-declining {{ color: #ef4444; }}
        .chart-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-top: 30px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Report Quality Evaluation Dashboard</h1>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Evaluations</div>
                <div class="metric-value">{summary.total_evaluations}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Average Score</div>
                <div class="metric-value">{summary.average_score:.1f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Passing Rate</div>
                <div class="metric-value">{summary.passing_rate:.0f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Highest Score</div>
                <div class="metric-value">{summary.highest_score:.1f}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 Top Performers</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Company</th>
                        <th>Score</th>
                        <th>Status</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for eval in top_performers[:5]:
            score_class = self._get_score_class(eval.overall_score)
            status_class = "status-passing" if eval.passes_quality_gates else "status-failing"
            status_text = "✓ Passing" if eval.passes_quality_gates else "✗ Failing"
            
            html += f"""
                    <tr>
                        <td><strong>{eval.ticker}</strong></td>
                        <td>{eval.company}</td>
                        <td><span class="score {score_class}">{eval.overall_score:.1f}</span></td>
                        <td><span class="{status_class}">{status_text}</span></td>
                        <td>{eval.evaluation_timestamp.strftime('%Y-%m-%d')}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📈 Recent Evaluations</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Company</th>
                        <th>Score</th>
                        <th>Trend</th>
                        <th>Key Recommendations</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for eval in recent_evaluations[:10]:
            score_class = self._get_score_class(eval.overall_score)
            
            # Get trend for this ticker
            history = self.storage.get_ticker_history(eval.ticker, limit=5)
            trend = history.score_trend
            trend_class = f"trend-{trend.value.lower()}"
            
            # Get top recommendation
            top_rec = eval.recommendations[0] if eval.recommendations else "No recommendations"
            
            html += f"""
                    <tr>
                        <td><strong>{eval.ticker}</strong></td>
                        <td>{eval.company}</td>
                        <td><span class="score {score_class}">{eval.overall_score:.1f}</span></td>
                        <td><span class="{trend_class}">{trend.value.replace('_', ' ').title()}</span></td>
                        <td>{top_rec}</td>
                    </tr>
            """
        
        html += f"""
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🎯 Quality Targets</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Target</th>
                        <th>Current Average</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Overall Score</td>
                        <td>≥ 8.0</td>
                        <td>{summary.average_score:.1f}</td>
                        <td>{'✓' if summary.average_score >= 8.0 else '✗'}</td>
                    </tr>
                    <tr>
                        <td>Quality Gates Passing</td>
                        <td>≥ 80%</td>
                        <td>{summary.passing_rate:.0f}%</td>
                        <td>{'✓' if summary.passing_rate >= 80 else '✗'}</td>
                    </tr>
                    <tr>
                        <td>BYD Benchmark</td>
                        <td>9.0</td>
                        <td>{summary.highest_score:.1f} (best)</td>
                        <td>{'✓' if summary.highest_score >= 9.0 else '✗'}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>⚠️ Needs Attention</h2>
            <p>The following tickers have consistently low scores and require improvement:</p>
            <ul>
        """
        
        for ticker in summary.needs_attention:
            html += f"<li><strong>{ticker}</strong> - Review recommendations and implement improvements</li>"
        
        html += f"""
            </ul>
        </div>
        
        <div class="timestamp">
            Last updated: {summary.last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _get_score_class(self, score: float) -> str:
        """Get CSS class for score.
        
        Args:
            score: Evaluation score
            
        Returns:
            CSS class name
        """
        if score >= 8.0:
            return "score-excellent"
        elif score >= 6.0:
            return "score-good"
        else:
            return "score-poor"
    
    def generate_ticker_report(
        self,
        ticker: str,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Generate detailed report for a ticker.
        
        Args:
            ticker: Company ticker
            output_path: Optional output path
            
        Returns:
            Ticker report data
        """
        # Get history
        history = self.storage.get_ticker_history(ticker)
        
        if not history.latest_evaluation:
            return {
                "ticker": ticker,
                "error": "No evaluation history available"
            }
        
        # Get trend analysis
        trends = self.trend_analyzer.analyze_ticker_trends(ticker)
        
        # Get patterns
        patterns = self.trend_analyzer.identify_patterns(ticker)
        
        # Get recommendations
        recommendations = self.recommendation_engine.generate_recommendations(
            history.latest_evaluation,
            history
        )
        
        # Get implementation roadmap
        roadmap = self.recommendation_engine.get_implementation_roadmap(ticker)
        
        # Generate visualizations
        trend_chart = self.trend_analyzer.create_trend_visualization(ticker)
        
        report = {
            "ticker": ticker,
            "company": history.company,
            "latest_evaluation": history.latest_evaluation.model_dump(),
            "trends": trends,
            "patterns": patterns,
            "recommendations": [r.model_dump() for r in recommendations],
            "roadmap": roadmap,
            "visualizations": {
                "trend_chart": trend_chart.hex() if trend_chart else None
            }
        }
        
        # Save if requested
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w") as f:
                json.dump(report, f, indent=2, default=str)
        
        return report
    
    def run_batch_evaluation(
        self,
        report_directory: Path,
        tickers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run batch evaluation on reports.
        
        Args:
            report_directory: Directory containing reports
            tickers: Optional list of tickers to evaluate
            
        Returns:
            Batch evaluation results
        """
        reports = []
        
        # Find reports
        if tickers:
            for ticker in tickers:
                report_path = report_directory / f"{ticker}_report.md"
                if report_path.exists():
                    content = report_path.read_text()
                    reports.append((content, ticker, ticker))
        else:
            for report_path in report_directory.glob("*_report.md"):
                ticker = report_path.stem.split('_')[0]
                content = report_path.read_text()
                reports.append((content, ticker, ticker))
        
        if not reports:
            return {"error": "No reports found"}
        
        # Run batch evaluation
        batch = self.runner.evaluate_batch(reports)
        
        # Generate comparison chart
        tickers_list = [r[1] for r in reports]
        comparison_chart = self.trend_analyzer.generate_comparison_chart(tickers_list)
        
        return {
            "batch_id": batch.batch_id,
            "total_evaluated": len(batch.evaluations),
            "average_score": batch.summary.average_score,
            "passing_rate": batch.summary.passing_rate,
            "top_performers": batch.summary.top_performers,
            "needs_attention": batch.summary.needs_attention,
            "comparison_chart": comparison_chart.hex() if comparison_chart else None
        }
    
    def export_metrics(self, output_path: Path) -> bool:
        """Export all metrics to JSON.
        
        Args:
            output_path: Output file path
            
        Returns:
            Success status
        """
        return self.storage.export_to_json(output_path)