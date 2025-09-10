"""Trend analysis and visualization for evaluation metrics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from investing_agent.schemas.evaluation_metrics import (
    EvaluationResult,
    EvaluationHistory,
    EvaluationDimension,
    DimensionalAnalysis,
    QualityTrend,
    EvaluationSummary,
)
from investing_agent.storage.metrics_storage import MetricsStorage


class TrendAnalyzer:
    """Analyzer for evaluation metric trends and patterns."""
    
    def __init__(self, storage: Optional[MetricsStorage] = None):
        """Initialize trend analyzer.
        
        Args:
            storage: Metrics storage instance
        """
        self.storage = storage or MetricsStorage()
        
        # Set professional style
        sns.set_style("whitegrid")
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    
    def analyze_ticker_trends(self, ticker: str) -> Dict[str, Any]:
        """Analyze trends for a specific ticker.
        
        Args:
            ticker: Company ticker
            
        Returns:
            Trend analysis results
        """
        history = self.storage.get_ticker_history(ticker)
        
        if not history.evaluations:
            return {
                "ticker": ticker,
                "trend": QualityTrend.INSUFFICIENT_DATA,
                "message": "No evaluation history available"
            }
        
        # Overall trend
        overall_trend = history.score_trend
        
        # Dimensional trends
        dimensional_analysis = self.storage.get_dimensional_analysis(ticker)
        
        # Recent performance
        recent_evals = history.evaluations[:5]
        recent_avg = sum(e.overall_score for e in recent_evals) / len(recent_evals)
        
        # Historical average
        historical_avg = history.average_score
        
        # Improvement rate
        if len(history.evaluations) >= 2:
            first_score = history.evaluations[-1].overall_score
            latest_score = history.evaluations[0].overall_score
            improvement = ((latest_score - first_score) / first_score) * 100
        else:
            improvement = 0
        
        return {
            "ticker": ticker,
            "company": history.company,
            "trend": overall_trend,
            "latest_score": history.latest_evaluation.overall_score if history.latest_evaluation else 0,
            "recent_average": recent_avg,
            "historical_average": historical_avg,
            "improvement_percentage": improvement,
            "dimensional_trends": dimensional_analysis,
            "total_evaluations": len(history.evaluations),
            "quality_gates_passing": history.latest_evaluation.passes_quality_gates if history.latest_evaluation else False
        }
    
    def identify_patterns(self, ticker: str) -> Dict[str, Any]:
        """Identify patterns in evaluation metrics.
        
        Args:
            ticker: Company ticker
            
        Returns:
            Pattern analysis
        """
        history = self.storage.get_ticker_history(ticker)
        
        if len(history.evaluations) < 3:
            return {"patterns": [], "message": "Insufficient data for pattern analysis"}
        
        patterns = []
        
        # Check for consistent improvement
        scores = [e.overall_score for e in history.evaluations]
        if all(scores[i] >= scores[i+1] for i in range(len(scores)-1)):
            patterns.append("consistent_improvement")
        
        # Check for volatility
        score_std = np.std(scores)
        if score_std > 1.5:
            patterns.append("high_volatility")
        elif score_std < 0.5:
            patterns.append("stable_performance")
        
        # Check for dimension-specific issues
        dimensional_analysis = self.storage.get_dimensional_analysis(ticker)
        weak_dimensions = []
        strong_dimensions = []
        
        for dim, analysis in dimensional_analysis.items():
            if analysis.current_score < 6.0:
                weak_dimensions.append(dim.value)
            elif analysis.current_score >= 8.0:
                strong_dimensions.append(dim.value)
        
        if weak_dimensions:
            patterns.append(f"weak_in_{','.join(weak_dimensions)}")
        if strong_dimensions:
            patterns.append(f"strong_in_{','.join(strong_dimensions)}")
        
        # Check for plateauing
        if len(scores) >= 5:
            recent_scores = scores[:5]
            if max(recent_scores) - min(recent_scores) < 0.5:
                patterns.append("plateauing")
        
        return {
            "ticker": ticker,
            "patterns": patterns,
            "score_volatility": score_std,
            "weak_dimensions": weak_dimensions,
            "strong_dimensions": strong_dimensions
        }
    
    def create_trend_visualization(self, ticker: str, output_path: Optional[Path] = None) -> bytes:
        """Create trend visualization for a ticker.
        
        Args:
            ticker: Company ticker
            output_path: Optional path to save image
            
        Returns:
            PNG bytes of visualization
        """
        history = self.storage.get_ticker_history(ticker)
        
        if len(history.evaluations) < 2:
            # Create placeholder image
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.text(0.5, 0.5, f"Insufficient data for {ticker}", 
                   ha='center', va='center', fontsize=16)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
        else:
            fig = self._create_trend_figure(history, ticker)
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        png_bytes = buffer.getvalue()
        
        # Save to file if requested
        if output_path:
            output_path.write_bytes(png_bytes)
        
        return png_bytes
    
    def _create_trend_figure(self, history: EvaluationHistory, ticker: str) -> Figure:
        """Create comprehensive trend figure.
        
        Args:
            history: Evaluation history
            ticker: Company ticker
            
        Returns:
            Matplotlib figure
        """
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # Overall score trend
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_overall_trend(ax1, history)
        
        # Dimensional scores
        ax2 = fig.add_subplot(gs[1, :2])
        self._plot_dimensional_scores(ax2, history)
        
        # Hard metrics
        ax3 = fig.add_subplot(gs[1, 2])
        self._plot_hard_metrics(ax3, history)
        
        # Score distribution
        ax4 = fig.add_subplot(gs[2, 0])
        self._plot_score_distribution(ax4, history)
        
        # Quality gates
        ax5 = fig.add_subplot(gs[2, 1])
        self._plot_quality_gates(ax5, history)
        
        # Improvement summary
        ax6 = fig.add_subplot(gs[2, 2])
        self._plot_improvement_summary(ax6, history)
        
        # Main title
        fig.suptitle(f"Evaluation Trends: {history.company} ({ticker})", 
                    fontsize=16, fontweight='bold', y=0.98)
        
        return fig
    
    def _plot_overall_trend(self, ax, history: EvaluationHistory):
        """Plot overall score trend."""
        evaluations = sorted(history.evaluations, key=lambda e: e.evaluation_timestamp)
        
        timestamps = [e.evaluation_timestamp for e in evaluations]
        scores = [e.overall_score for e in evaluations]
        
        # Main trend line
        ax.plot(timestamps, scores, 'b-', linewidth=2, label='Overall Score')
        ax.scatter(timestamps, scores, color='blue', s=50, zorder=5)
        
        # Target lines
        ax.axhline(y=9.0, color='green', linestyle='--', alpha=0.5, label='Excellence (9.0)')
        ax.axhline(y=8.0, color='orange', linestyle='--', alpha=0.5, label='Target (8.0)')
        ax.axhline(y=6.0, color='red', linestyle='--', alpha=0.5, label='Minimum (6.0)')
        
        # Trend line
        if len(scores) >= 2:
            z = np.polyfit(range(len(scores)), scores, 1)
            p = np.poly1d(z)
            ax.plot(timestamps, p(range(len(scores))), 'g--', alpha=0.5, label='Trend')
        
        ax.set_xlabel('Evaluation Date')
        ax.set_ylabel('Overall Score')
        ax.set_title('Overall Quality Score Trend')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 10)
        
        # Rotate x labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def _plot_dimensional_scores(self, ax, history: EvaluationHistory):
        """Plot dimensional score trends."""
        latest_eval = history.latest_evaluation
        
        if not latest_eval:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.axis('off')
            return
        
        dimensions = [s.dimension.value for s in latest_eval.dimensional_scores]
        scores = [s.score for s in latest_eval.dimensional_scores]
        
        # Create bar chart
        colors = ['green' if s >= 8 else 'orange' if s >= 6 else 'red' for s in scores]
        bars = ax.bar(range(len(dimensions)), scores, color=colors, alpha=0.7)
        
        # Add value labels
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{score:.1f}', ha='center', va='bottom')
        
        ax.set_xticks(range(len(dimensions)))
        ax.set_xticklabels([d.replace('_', '\n') for d in dimensions], rotation=0)
        ax.set_ylabel('Score')
        ax.set_title('Latest Dimensional Scores')
        ax.set_ylim(0, 10)
        ax.grid(True, alpha=0.3, axis='y')
    
    def _plot_hard_metrics(self, ax, history: EvaluationHistory):
        """Plot hard metrics status."""
        latest_eval = history.latest_evaluation
        
        if not latest_eval:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center')
            ax.axis('off')
            return
        
        metrics = latest_eval.hard_metrics
        
        # Create pie chart for pass/fail metrics
        passed = sum([
            metrics.evidence_coverage >= 0.80,
            metrics.citation_density >= 0.70,
            metrics.contradiction_rate <= 0.20,
            metrics.fixture_stability
        ])
        failed = 4 - passed
        
        colors = ['green', 'red']
        sizes = [passed, failed]
        labels = [f'Passing\n({passed}/4)', f'Failing\n({failed}/4)']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%',
               startangle=90, textprops={'fontsize': 10})
        ax.set_title('Hard Metrics Status')
    
    def _plot_score_distribution(self, ax, history: EvaluationHistory):
        """Plot score distribution histogram."""
        scores = [e.overall_score for e in history.evaluations]
        
        ax.hist(scores, bins=10, range=(0, 10), color='blue', alpha=0.7, edgecolor='black')
        ax.axvline(x=np.mean(scores), color='red', linestyle='--', 
                  label=f'Mean: {np.mean(scores):.1f}')
        ax.axvline(x=np.median(scores), color='green', linestyle='--',
                  label=f'Median: {np.median(scores):.1f}')
        
        ax.set_xlabel('Score')
        ax.set_ylabel('Frequency')
        ax.set_title('Score Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    
    def _plot_quality_gates(self, ax, history: EvaluationHistory):
        """Plot quality gates pass rate over time."""
        evaluations = sorted(history.evaluations, key=lambda e: e.evaluation_timestamp)
        
        if len(evaluations) < 2:
            ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center')
            ax.axis('off')
            return
        
        # Calculate rolling pass rate
        window = min(5, len(evaluations))
        pass_rates = []
        
        for i in range(len(evaluations) - window + 1):
            window_evals = evaluations[i:i+window]
            passed = sum(1 for e in window_evals if e.passes_quality_gates)
            pass_rates.append((passed / window) * 100)
        
        ax.plot(range(len(pass_rates)), pass_rates, 'g-', linewidth=2)
        ax.fill_between(range(len(pass_rates)), 0, pass_rates, alpha=0.3, color='green')
        
        ax.set_xlabel(f'Evaluation Window ({window}-eval rolling)')
        ax.set_ylabel('Pass Rate (%)')
        ax.set_title('Quality Gates Pass Rate')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
    
    def _plot_improvement_summary(self, ax, history: EvaluationHistory):
        """Plot improvement summary."""
        trend = history.score_trend
        latest = history.latest_evaluation
        
        # Create summary text
        summary_text = f"Trend: {trend.value.replace('_', ' ').title()}\n\n"
        
        if latest:
            summary_text += f"Latest Score: {latest.overall_score:.1f}/10\n"
            summary_text += f"Average Score: {history.average_score:.1f}/10\n"
            summary_text += f"Total Evaluations: {len(history.evaluations)}\n\n"
            
            if latest.passes_quality_gates:
                summary_text += "✓ Passing Quality Gates"
            else:
                summary_text += "✗ Failing Quality Gates"
        
        ax.text(0.5, 0.5, summary_text, ha='center', va='center',
               fontsize=11, transform=ax.transAxes)
        ax.set_title('Summary')
        ax.axis('off')
    
    def generate_comparison_chart(
        self,
        tickers: List[str],
        output_path: Optional[Path] = None
    ) -> bytes:
        """Generate comparison chart for multiple tickers.
        
        Args:
            tickers: List of tickers to compare
            output_path: Optional output path
            
        Returns:
            PNG bytes
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Multi-Ticker Evaluation Comparison', fontsize=16, fontweight='bold')
        
        # Collect data
        ticker_data = []
        for ticker in tickers[:10]:  # Limit to 10 tickers
            history = self.storage.get_ticker_history(ticker)
            if history.latest_evaluation:
                ticker_data.append({
                    'ticker': ticker,
                    'score': history.latest_evaluation.overall_score,
                    'average': history.average_score,
                    'trend': history.score_trend,
                    'evaluations': len(history.evaluations)
                })
        
        if not ticker_data:
            fig.text(0.5, 0.5, 'No data available', ha='center', va='center')
        else:
            # Latest scores comparison
            ax = axes[0, 0]
            tickers_list = [d['ticker'] for d in ticker_data]
            scores = [d['score'] for d in ticker_data]
            colors = ['green' if s >= 8 else 'orange' if s >= 6 else 'red' for s in scores]
            ax.bar(tickers_list, scores, color=colors, alpha=0.7)
            ax.set_ylabel('Latest Score')
            ax.set_title('Latest Evaluation Scores')
            ax.set_ylim(0, 10)
            ax.grid(True, alpha=0.3, axis='y')
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Average scores
            ax = axes[0, 1]
            averages = [d['average'] for d in ticker_data]
            ax.bar(tickers_list, averages, color='blue', alpha=0.7)
            ax.set_ylabel('Average Score')
            ax.set_title('Historical Average Scores')
            ax.set_ylim(0, 10)
            ax.grid(True, alpha=0.3, axis='y')
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Trends
            ax = axes[1, 0]
            trend_counts = {}
            for d in ticker_data:
                trend = d['trend'].value
                trend_counts[trend] = trend_counts.get(trend, 0) + 1
            
            if trend_counts:
                ax.pie(trend_counts.values(), labels=trend_counts.keys(),
                      autopct='%1.0f%%', startangle=90)
                ax.set_title('Trend Distribution')
            
            # Evaluation counts
            ax = axes[1, 1]
            eval_counts = [d['evaluations'] for d in ticker_data]
            ax.bar(tickers_list, eval_counts, color='purple', alpha=0.7)
            ax.set_ylabel('Number of Evaluations')
            ax.set_title('Evaluation History Depth')
            ax.grid(True, alpha=0.3, axis='y')
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        png_bytes = buffer.getvalue()
        
        if output_path:
            output_path.write_bytes(png_bytes)
        
        return png_bytes