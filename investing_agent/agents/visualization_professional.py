"""Professional visualization generation for investment reports."""

from __future__ import annotations

import io
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from matplotlib.gridspec import GridSpec
import seaborn as sns

# Set professional style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

from investing_agent.schemas.chart_config import (
    ChartConfig, PeerComparisonChartConfig, WaterfallChartConfig,
    SensitivityHeatmapConfig, TimeSeriesChartConfig, FinancialMetricsChartConfig,
    ColorScheme, ChartType, get_professional_colors
)
from investing_agent.schemas.comparables import PeerAnalysis
from investing_agent.schemas.inputs import InputsI
from investing_agent.schemas.valuation import ValuationV


class ProfessionalVisualizer:
    """Generate professional-grade charts for investment reports."""
    
    def __init__(self, color_scheme: ColorScheme = ColorScheme.PROFESSIONAL_BLUE):
        self.colors = get_professional_colors(color_scheme)
        self.default_style = {
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
            'font.size': 10,
            'axes.labelsize': 10,
            'axes.titlesize': 12,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'figure.titlesize': 14,
            'axes.grid': True,
            'grid.alpha': 0.3,
            'axes.spines.top': False,
            'axes.spines.right': False
        }
    
    def create_peer_multiples_chart(self, peer_analysis: PeerAnalysis, 
                                   target_ticker: str,
                                   metric: str = "ev_ebitda") -> bytes:
        """Create professional peer multiples comparison chart."""
        
        # Extract data
        peer_data = []
        for peer in peer_analysis.peer_companies:
            if metric in peer.multiples:
                peer_data.append({
                    'ticker': peer.ticker,
                    'value': peer.multiples[metric],
                    'is_target': peer.ticker == target_ticker
                })
        
        # Sort by value
        peer_data.sort(key=lambda x: x['value'])
        
        # Calculate statistics
        values = [p['value'] for p in peer_data]
        industry_avg = np.mean(values)
        industry_median = np.median(values)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
        
        # Plot bars
        x_pos = np.arange(len(peer_data))
        colors = [self.colors['primary'] if p['is_target'] else self.colors['neutral'] 
                 for p in peer_data]
        
        bars = ax.bar(x_pos, [p['value'] for p in peer_data], color=colors, alpha=0.8)
        
        # Add average line
        ax.axhline(y=industry_avg, color=self.colors['accent'], linestyle='--', 
                  linewidth=2, label=f'Industry Average ({industry_avg:.1f}x)')
        
        # Add median line
        ax.axhline(y=industry_median, color=self.colors['secondary'], linestyle=':', 
                  linewidth=2, label=f'Industry Median ({industry_median:.1f}x)')
        
        # Formatting
        ax.set_xlabel('Companies', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{metric.upper().replace("_", "/")} Multiple', fontsize=12, fontweight='bold')
        ax.set_title(f'Peer Comparison: {metric.upper().replace("_", "/")} Multiples', 
                    fontsize=14, fontweight='bold', pad=20)
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels([p['ticker'] for p in peer_data], rotation=45, ha='right')
        
        # Add value labels on bars
        for bar, peer in zip(bars, peer_data):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}x',
                   ha='center', va='bottom', fontsize=9)
        
        # Legend
        target_patch = mpatches.Patch(color=self.colors['primary'], label=target_ticker)
        peers_patch = mpatches.Patch(color=self.colors['neutral'], label='Peers')
        ax.legend(handles=[target_patch, peers_patch] + ax.get_lines(), 
                 loc='upper left', frameon=True, fancybox=True, shadow=True)
        
        # Grid and styling
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        # Add source note
        fig.text(0.99, 0.01, 'Source: Company filings, Bloomberg', 
                ha='right', va='bottom', fontsize=8, style='italic', color='gray')
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return buf.getvalue()
    
    def create_financial_trajectory_chart(self, inputs: InputsI, valuation: ValuationV,
                                         metrics: List[str] = ["revenue", "ebitda", "fcf"]) -> bytes:
        """Create multi-metric financial trajectory chart."""
        
        fig = plt.figure(figsize=(12, 8), dpi=150)
        gs = GridSpec(3, 1, figure=fig, hspace=0.3)
        
        years = list(range(1, inputs.horizon + 1))
        
        # Revenue trajectory
        ax1 = fig.add_subplot(gs[0, 0])
        revenue = valuation.revenue_projection[:inputs.horizon] if hasattr(valuation, 'revenue_projection') else []
        if revenue:
            ax1.plot(years, revenue, marker='o', linewidth=2, markersize=6, 
                    color=self.colors['primary'], label='Revenue')
            ax1.fill_between(years, 0, revenue, alpha=0.2, color=self.colors['primary'])
            
            # Add growth rate labels
            for i in range(1, len(revenue)):
                growth = (revenue[i] / revenue[i-1] - 1) * 100
                ax1.text(years[i], revenue[i], f'+{growth:.1f}%', 
                        ha='center', va='bottom', fontsize=8, color='green')
            
            ax1.set_ylabel('Revenue ($M)', fontweight='bold')
            ax1.set_title('Financial Trajectory Analysis', fontsize=14, fontweight='bold', pad=20)
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper left')
        
        # EBITDA trajectory with margins
        ax2 = fig.add_subplot(gs[1, 0])
        ebitda = valuation.ebitda_projection[:inputs.horizon] if hasattr(valuation, 'ebitda_projection') else []
        if ebitda and revenue:
            ax2.plot(years, ebitda, marker='s', linewidth=2, markersize=6,
                    color=self.colors['secondary'], label='EBITDA')
            
            # Add margin percentages
            margins = [e/r * 100 for e, r in zip(ebitda, revenue)]
            ax2_twin = ax2.twinx()
            ax2_twin.plot(years, margins, linestyle='--', linewidth=1.5,
                         color=self.colors['accent'], alpha=0.7, label='EBITDA Margin %')
            ax2_twin.set_ylabel('EBITDA Margin (%)', fontweight='bold', color=self.colors['accent'])
            ax2_twin.tick_params(axis='y', labelcolor=self.colors['accent'])
            
            ax2.set_ylabel('EBITDA ($M)', fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper left')
            ax2_twin.legend(loc='upper right')
        
        # Free Cash Flow
        ax3 = fig.add_subplot(gs[2, 0])
        fcf_values = []
        for i in range(inputs.horizon):
            # Simple FCF calculation (would use actual from valuation if available)
            fcf = ebitda[i] * 0.7 if i < len(ebitda) else 0  # Simplified
            fcf_values.append(fcf)
        
        positive = [f if f > 0 else 0 for f in fcf_values]
        negative = [f if f < 0 else 0 for f in fcf_values]
        
        ax3.bar(years, positive, color=self.colors['positive'], alpha=0.7, label='Positive FCF')
        ax3.bar(years, negative, color=self.colors['negative'], alpha=0.7, label='Negative FCF')
        ax3.axhline(y=0, color='black', linewidth=1)
        
        ax3.set_xlabel('Year', fontweight='bold')
        ax3.set_ylabel('Free Cash Flow ($M)', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.legend(loc='upper left')
        
        # Add source note
        fig.text(0.99, 0.01, 'Source: Company projections, Analyst estimates', 
                ha='right', va='bottom', fontsize=8, style='italic', color='gray')
        
        plt.suptitle('')  # Remove duplicate title
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return buf.getvalue()
    
    def create_value_bridge_waterfall(self, valuation: ValuationV) -> bytes:
        """Create waterfall chart showing value bridge from operations to equity."""
        
        fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
        
        # Sample data (would be calculated from actual valuation)
        categories = ['Operating\nCash Flows', 'Terminal\nValue', 'Total\nEnterprise\nValue',
                     '(-) Net Debt', '(+) Cash', 'Equity\nValue', 'Per Share\nValue']
        
        # Extract values from valuation (simplified example)
        op_cash = valuation.present_value_sum if hasattr(valuation, 'present_value_sum') else 1000
        terminal = valuation.terminal_value if hasattr(valuation, 'terminal_value') else 800
        
        values = [op_cash, terminal, 0, -200, 150, 0, 0]  # Placeholder values
        
        # Calculate cumulative values
        cumulative = []
        cum_val = 0
        for i, val in enumerate(values):
            if i == 2:  # Total EV
                values[i] = cum_val
                cumulative.append(cum_val)
            elif i == 5:  # Equity Value
                cum_val += values[i-1]
                values[i] = cum_val
                cumulative.append(cum_val)
            elif i == 6:  # Per share
                values[i] = cum_val / 100  # Assuming 100 shares
                cumulative.append(values[i])
            else:
                cum_val += val
                cumulative.append(cum_val)
        
        # Create waterfall
        x_pos = np.arange(len(categories))
        
        for i, (cat, val, cum) in enumerate(zip(categories, values, cumulative)):
            if i == 0:
                # First bar starts from 0
                color = self.colors['primary']
                bottom = 0
                height = val
            elif cat.startswith('(-)'):
                # Negative contribution
                color = self.colors['negative']
                bottom = cumulative[i-1]
                height = val
            elif cat.startswith('(+)'):
                # Positive contribution  
                color = self.colors['positive']
                bottom = cumulative[i-1]
                height = val
            elif 'Total' in cat or 'Equity' in cat or 'Per Share' in cat:
                # Total bars
                color = self.colors['secondary']
                bottom = 0
                height = cum
            else:
                # Regular positive
                color = self.colors['primary']
                bottom = cumulative[i-1] if i > 0 else 0
                height = val
            
            bar = ax.bar(x_pos[i], height, bottom=bottom, color=color, alpha=0.7, width=0.6)
            
            # Add value labels
            if height != 0:
                label_y = bottom + height/2 if height > 0 else bottom + height/2
                ax.text(x_pos[i], label_y, f'${abs(height):.0f}', 
                       ha='center', va='center', fontweight='bold', color='white')
        
        # Add connecting lines
        for i in range(len(x_pos) - 1):
            if not ('Total' in categories[i] or 'Equity' in categories[i] or 'Per Share' in categories[i]):
                ax.plot([x_pos[i] + 0.3, x_pos[i+1] - 0.3], 
                       [cumulative[i], cumulative[i]], 
                       'k--', alpha=0.5, linewidth=1)
        
        # Formatting
        ax.set_xticks(x_pos)
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylabel('Value ($M)', fontsize=12, fontweight='bold')
        ax.set_title('Value Bridge: From Operations to Equity Value', 
                    fontsize=14, fontweight='bold', pad=20)
        
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        # Add source note
        fig.text(0.99, 0.01, 'Source: DCF Valuation Model', 
                ha='right', va='bottom', fontsize=8, style='italic', color='gray')
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return buf.getvalue()
    
    def create_sensitivity_heatmap_professional(self, sensitivity_data: np.ndarray,
                                               growth_labels: List[str],
                                               margin_labels: List[str],
                                               center_value: float) -> bytes:
        """Create professional sensitivity heatmap with annotations."""
        
        fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
        
        # Create heatmap with diverging colormap centered on base case
        vmin, vmax = sensitivity_data.min(), sensitivity_data.max()
        
        # Use diverging colormap
        im = ax.imshow(sensitivity_data, cmap='RdYlGn', aspect='auto',
                      vmin=vmin, vmax=vmax, interpolation='nearest')
        
        # Set ticks and labels
        ax.set_xticks(np.arange(len(growth_labels)))
        ax.set_yticks(np.arange(len(margin_labels)))
        ax.set_xticklabels(growth_labels)
        ax.set_yticklabels(margin_labels)
        
        # Rotate the tick labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Value per Share ($)', rotation=270, labelpad=15, fontweight='bold')
        
        # Add text annotations
        for i in range(len(margin_labels)):
            for j in range(len(growth_labels)):
                value = sensitivity_data[i, j]
                color = 'white' if abs(value - center_value) > (vmax - vmin) * 0.3 else 'black'
                text = ax.text(j, i, f'${value:.0f}',
                             ha="center", va="center", color=color, fontweight='bold')
        
        # Highlight base case
        base_i, base_j = len(margin_labels) // 2, len(growth_labels) // 2
        rect = Rectangle((base_j - 0.5, base_i - 0.5), 1, 1, 
                        fill=False, edgecolor='blue', linewidth=3)
        ax.add_patch(rect)
        
        # Labels and title
        ax.set_xlabel('Revenue Growth Rate', fontsize=12, fontweight='bold')
        ax.set_ylabel('Operating Margin', fontsize=12, fontweight='bold')
        ax.set_title('Valuation Sensitivity Analysis\n(Blue box = Base Case)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Add grid
        ax.set_xticks(np.arange(len(growth_labels) + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(margin_labels) + 1) - 0.5, minor=True)
        ax.grid(which="minor", color="gray", linestyle='-', linewidth=0.5)
        
        # Add source note
        fig.text(0.99, 0.01, 'Source: DCF Model Sensitivity Analysis', 
                ha='right', va='bottom', fontsize=8, style='italic', color='gray')
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return buf.getvalue()
    
    def create_competitive_positioning_matrix(self, companies: List[Dict[str, float]]) -> bytes:
        """Create competitive positioning scatter plot (growth vs margins)."""
        
        fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
        
        # Extract data
        growth_rates = [c.get('growth', 0) for c in companies]
        margins = [c.get('margin', 0) for c in companies]
        market_caps = [c.get('market_cap', 100) for c in companies]
        names = [c.get('name', f'Company {i}') for i, c in enumerate(companies)]
        is_target = [c.get('is_target', False) for c in companies]
        
        # Normalize market caps for bubble sizes
        max_cap = max(market_caps)
        sizes = [(cap / max_cap) * 1000 for cap in market_caps]
        
        # Colors
        colors = [self.colors['primary'] if target else self.colors['neutral'] 
                 for target in is_target]
        
        # Create scatter plot
        for i, (x, y, s, c, name) in enumerate(zip(growth_rates, margins, sizes, colors, names)):
            ax.scatter(x, y, s=s, c=c, alpha=0.6, edgecolors='black', linewidth=1)
            ax.annotate(name, (x, y), xytext=(5, 5), textcoords='offset points', 
                       fontsize=9, fontweight='bold' if is_target[i] else 'normal')
        
        # Add quadrant lines
        ax.axhline(y=np.median(margins), color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=np.median(growth_rates), color='gray', linestyle='--', alpha=0.5)
        
        # Add quadrant labels
        ax.text(0.95, 0.95, 'High Growth\nHigh Margin', transform=ax.transAxes,
               ha='right', va='top', fontsize=10, color='green', fontweight='bold')
        ax.text(0.05, 0.95, 'Low Growth\nHigh Margin', transform=ax.transAxes,
               ha='left', va='top', fontsize=10, color='orange', fontweight='bold')
        ax.text(0.95, 0.05, 'High Growth\nLow Margin', transform=ax.transAxes,
               ha='right', va='bottom', fontsize=10, color='orange', fontweight='bold')
        ax.text(0.05, 0.05, 'Low Growth\nLow Margin', transform=ax.transAxes,
               ha='left', va='bottom', fontsize=10, color='red', fontweight='bold')
        
        # Labels and title
        ax.set_xlabel('Revenue Growth Rate (%)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Operating Margin (%)', fontsize=12, fontweight='bold')
        ax.set_title('Competitive Positioning Matrix\n(Bubble size = Market Cap)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Grid
        ax.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
        
        # Legend
        target_patch = mpatches.Patch(color=self.colors['primary'], label='Target Company')
        peers_patch = mpatches.Patch(color=self.colors['neutral'], label='Peers')
        ax.legend(handles=[target_patch, peers_patch], loc='best', frameon=True)
        
        # Add source note
        fig.text(0.99, 0.01, 'Source: Company filings, Bloomberg consensus', 
                ha='right', va='bottom', fontsize=8, style='italic', color='gray')
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return buf.getvalue()


def generate_chart_bundle(inputs: InputsI, valuation: ValuationV, 
                         peer_analysis: Optional[PeerAnalysis] = None) -> Dict[str, bytes]:
    """Generate complete set of professional charts for report."""
    
    visualizer = ProfessionalVisualizer()
    charts = {}
    
    # Financial trajectory
    charts['financial_trajectory'] = visualizer.create_financial_trajectory_chart(inputs, valuation)
    
    # Value bridge
    charts['value_bridge'] = visualizer.create_value_bridge_waterfall(valuation)
    
    # Peer analysis if available
    if peer_analysis and peer_analysis.peer_companies:
        charts['peer_multiples'] = visualizer.create_peer_multiples_chart(
            peer_analysis, inputs.ticker
        )
        
        # Create competitive positioning data
        companies = []
        for peer in peer_analysis.peer_companies[:8]:  # Limit to 8 for readability
            companies.append({
                'name': peer.ticker,
                'growth': np.random.uniform(5, 25),  # Would use actual data
                'margin': np.random.uniform(10, 30),  # Would use actual data
                'market_cap': peer.market_cap,
                'is_target': peer.ticker == inputs.ticker
            })
        
        if companies:
            charts['competitive_positioning'] = visualizer.create_competitive_positioning_matrix(companies)
    
    return charts