"""Chart configuration schemas for professional visualizations."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from enum import Enum


class ChartType(str, Enum):
    """Supported chart types for professional reports."""
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    WATERFALL = "waterfall"
    STACKED_BAR = "stacked_bar"
    AREA = "area"
    COMBO = "combo"
    PIE = "pie"
    HORIZONTAL_BAR = "horizontal_bar"


class ColorScheme(str, Enum):
    """Professional color schemes."""
    PROFESSIONAL_BLUE = "professional_blue"
    FINANCE_GREEN = "finance_green"
    RISK_GRADIENT = "risk_gradient"
    PEER_COMPARISON = "peer_comparison"
    PERFORMANCE = "performance"


class ChartStyle(BaseModel):
    """Styling configuration for charts."""
    
    color_scheme: ColorScheme = Field(default=ColorScheme.PROFESSIONAL_BLUE)
    font_family: str = Field(default="Arial, sans-serif")
    title_font_size: int = Field(default=14)
    label_font_size: int = Field(default=10)
    legend_position: Literal["top", "bottom", "left", "right", "none"] = Field(default="bottom")
    grid_alpha: float = Field(default=0.3)
    dpi: int = Field(default=150)
    figure_size: tuple[float, float] = Field(default=(8, 5))
    
    # Professional styling elements
    show_data_labels: bool = Field(default=False)
    show_trend_line: bool = Field(default=False)
    show_average_line: bool = Field(default=False)
    highlight_current: bool = Field(default=True)
    

class ChartData(BaseModel):
    """Data structure for chart inputs."""
    
    x_values: List[Any] = Field(description="X-axis values")
    y_values: List[float] = Field(description="Y-axis values")
    series_name: Optional[str] = Field(None, description="Name of the data series")
    
    # Additional series for multi-series charts
    additional_series: Optional[Dict[str, List[float]]] = Field(None)
    
    # Metadata for enhanced visualizations
    annotations: Optional[List[Dict[str, Any]]] = Field(None)
    benchmarks: Optional[Dict[str, float]] = Field(None)
    

class ChartConfig(BaseModel):
    """Complete configuration for a professional chart."""
    
    chart_type: ChartType = Field(description="Type of chart to generate")
    title: str = Field(description="Chart title")
    subtitle: Optional[str] = Field(None, description="Chart subtitle")
    
    # Axes configuration
    x_label: str = Field(description="X-axis label")
    y_label: str = Field(description="Y-axis label")
    x_format: Optional[str] = Field(None, description="X-axis value format (e.g., '%Y-%m', '%.1f%%')")
    y_format: Optional[str] = Field(None, description="Y-axis value format")
    
    # Data
    data: ChartData = Field(description="Chart data")
    
    # Styling
    style: ChartStyle = Field(default_factory=ChartStyle)
    
    # Professional elements
    source_note: Optional[str] = Field(None, description="Source attribution")
    footnote: Optional[str] = Field(None, description="Additional footnote")
    

class PeerComparisonChartConfig(ChartConfig):
    """Configuration for peer comparison charts."""
    
    chart_type: ChartType = Field(default=ChartType.BAR)
    
    # Peer-specific settings
    peer_names: List[str] = Field(description="Names of peer companies")
    target_company: str = Field(description="Target company to highlight")
    industry_average: Optional[float] = Field(None, description="Industry average to display")
    show_quartiles: bool = Field(default=False, description="Show quartile lines")
    

class WaterfallChartConfig(ChartConfig):
    """Configuration for waterfall charts."""
    
    chart_type: ChartType = Field(default=ChartType.WATERFALL)
    
    # Waterfall-specific settings
    categories: List[str] = Field(description="Category labels for each bar")
    values: List[float] = Field(description="Values for each category")
    is_total: List[bool] = Field(description="Whether each bar is a total/subtotal")
    
    # Formatting
    positive_color: str = Field(default="#2E7D32")
    negative_color: str = Field(default="#C62828")
    total_color: str = Field(default="#1565C0")
    connector_color: str = Field(default="#666666")
    

class SensitivityHeatmapConfig(ChartConfig):
    """Configuration for sensitivity heatmaps."""
    
    chart_type: ChartType = Field(default=ChartType.HEATMAP)
    
    # Heatmap-specific settings
    row_labels: List[str] = Field(description="Row axis labels")
    col_labels: List[str] = Field(description="Column axis labels")
    grid_values: List[List[float]] = Field(description="2D grid of values")
    
    # Color mapping
    colormap: str = Field(default="RdYlGn")
    center_value: Optional[float] = Field(None, description="Value to center colormap on")
    show_values: bool = Field(default=True, description="Display values in cells")
    value_format: str = Field(default=".1f", description="Format for cell values")
    

class TimeSeriesChartConfig(ChartConfig):
    """Configuration for time series charts."""
    
    chart_type: ChartType = Field(default=ChartType.LINE)
    
    # Time series specific
    date_values: List[str] = Field(description="Date strings for x-axis")
    series_data: Dict[str, List[float]] = Field(description="Multiple series data")
    
    # Formatting
    show_markers: bool = Field(default=True)
    smooth_lines: bool = Field(default=False)
    fill_area: bool = Field(default=False)
    
    # Annotations
    highlight_periods: Optional[List[Dict[str, Any]]] = Field(None)
    event_markers: Optional[List[Dict[str, Any]]] = Field(None)
    

class FinancialMetricsChartConfig(ChartConfig):
    """Configuration for financial metrics visualization."""
    
    # Financial-specific formatting
    currency_symbol: str = Field(default="$")
    show_cagr: bool = Field(default=False)
    show_growth_rates: bool = Field(default=False)
    
    # Comparison elements
    prior_year_comparison: bool = Field(default=False)
    budget_comparison: bool = Field(default=False)
    forecast_shading: bool = Field(default=True)
    

class ChartBundle(BaseModel):
    """Collection of charts for a complete report."""
    
    # Core valuation charts
    sensitivity_analysis: Optional[SensitivityHeatmapConfig] = None
    driver_paths: Optional[TimeSeriesChartConfig] = None
    value_bridge: Optional[WaterfallChartConfig] = None
    
    # Peer analysis charts
    peer_multiples: Optional[PeerComparisonChartConfig] = None
    peer_margins: Optional[PeerComparisonChartConfig] = None
    peer_growth: Optional[PeerComparisonChartConfig] = None
    
    # Financial trajectory charts
    revenue_trajectory: Optional[TimeSeriesChartConfig] = None
    margin_evolution: Optional[TimeSeriesChartConfig] = None
    cash_flow_profile: Optional[TimeSeriesChartConfig] = None
    
    # Market analysis charts
    market_share: Optional[ChartConfig] = None
    competitive_positioning: Optional[ChartConfig] = None
    
    # Risk analysis charts
    scenario_analysis: Optional[ChartConfig] = None
    risk_matrix: Optional[ChartConfig] = None
    

def get_professional_colors(scheme: ColorScheme) -> Dict[str, str]:
    """Get color palette for a given scheme."""
    
    palettes = {
        ColorScheme.PROFESSIONAL_BLUE: {
            "primary": "#1565C0",
            "secondary": "#42A5F5",
            "accent": "#90CAF9",
            "negative": "#EF5350",
            "positive": "#66BB6A",
            "neutral": "#78909C"
        },
        ColorScheme.FINANCE_GREEN: {
            "primary": "#2E7D32",
            "secondary": "#66BB6A",
            "accent": "#A5D6A7",
            "negative": "#D32F2F",
            "positive": "#388E3C",
            "neutral": "#607D8B"
        },
        ColorScheme.RISK_GRADIENT: {
            "low": "#4CAF50",
            "medium": "#FFC107",
            "high": "#FF5722",
            "critical": "#B71C1C",
            "safe": "#1B5E20",
            "neutral": "#9E9E9E"
        },
        ColorScheme.PEER_COMPARISON: {
            "target": "#1976D2",
            "peers": "#78909C",
            "average": "#FF6F00",
            "top_quartile": "#43A047",
            "bottom_quartile": "#E53935",
            "median": "#FDD835"
        },
        ColorScheme.PERFORMANCE: {
            "actual": "#303F9F",
            "forecast": "#7986CB",
            "budget": "#FF9800",
            "prior_year": "#9E9E9E",
            "variance_positive": "#4CAF50",
            "variance_negative": "#F44336"
        }
    }
    
    return palettes.get(scheme, palettes[ColorScheme.PROFESSIONAL_BLUE])