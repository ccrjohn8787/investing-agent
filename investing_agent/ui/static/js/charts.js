/**
 * Chart.js configurations and initialization for investment reports
 */

// Chart color scheme
const chartColors = {
    primary: '#2563eb',
    secondary: '#1e40af',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    grid: '#e5e7eb',
    text: '#6b7280'
};

// Dark mode colors
const darkChartColors = {
    primary: '#3b82f6',
    secondary: '#60a5fa',
    success: '#34d399',
    warning: '#fbbf24',
    danger: '#f87171',
    grid: '#374151',
    text: '#9ca3af'
};

/**
 * Initialize revenue and profitability chart
 */
function initRevenueChart(data) {
    const ctx = document.getElementById('revenueChart');
    if (!ctx) return;
    
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const colors = isDark ? darkChartColors : chartColors;
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.years || ['Y1', 'Y2', 'Y3', 'Y4', 'Y5'],
            datasets: [
                {
                    label: 'Revenue (B)',
                    data: data.revenue || [],
                    borderColor: colors.primary,
                    backgroundColor: colors.primary + '20',
                    yAxisID: 'y',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Operating Margin (%)',
                    data: data.margin || [],
                    borderColor: colors.success,
                    backgroundColor: colors.success + '20',
                    yAxisID: 'y1',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: colors.text,
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: isDark ? '#1f2937' : '#ffffff',
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                if (context.datasetIndex === 0) {
                                    label += '$' + context.parsed.y.toFixed(1) + 'B';
                                } else {
                                    label += context.parsed.y.toFixed(1) + '%';
                                }
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: colors.grid,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: colors.grid,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text,
                        callback: function(value) {
                            return '$' + value + 'B';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Revenue',
                        color: colors.text
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text,
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Margin',
                        color: colors.text
                    }
                }
            }
        }
    });
}

/**
 * Initialize waterfall chart for valuation bridge
 */
function initWaterfallChart(data) {
    const ctx = document.getElementById('waterfallChart');
    if (!ctx) return;
    
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const colors = isDark ? darkChartColors : chartColors;
    
    // Calculate cumulative values for waterfall
    const baseValue = data.baseValue || 100;
    let cumulative = baseValue;
    const cumulativeData = [baseValue];
    const floatingBars = [[0, baseValue]];
    
    data.changes.forEach(change => {
        const newCumulative = cumulative + change;
        floatingBars.push([Math.min(cumulative, newCumulative), Math.abs(change)]);
        cumulative = newCumulative;
        cumulativeData.push(cumulative);
    });
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || ['Base', 'Growth Impact', 'Margin Impact', 'WACC Impact', 'Final Value'],
            datasets: [{
                label: 'Valuation Bridge',
                data: floatingBars,
                backgroundColor: function(context) {
                    const index = context.dataIndex;
                    if (index === 0 || index === floatingBars.length - 1) {
                        return colors.primary;
                    }
                    return data.changes[index - 1] >= 0 ? colors.success : colors.danger;
                },
                borderColor: function(context) {
                    const index = context.dataIndex;
                    if (index === 0 || index === floatingBars.length - 1) {
                        return colors.primary;
                    }
                    return data.changes[index - 1] >= 0 ? colors.success : colors.danger;
                },
                borderWidth: 1,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: isDark ? '#1f2937' : '#ffffff',
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            if (index === 0) {
                                return 'Base Value: $' + baseValue.toFixed(2);
                            } else if (index === floatingBars.length - 1) {
                                return 'Final Value: $' + cumulative.toFixed(2);
                            } else {
                                const change = data.changes[index - 1];
                                const sign = change >= 0 ? '+' : '';
                                return 'Impact: ' + sign + '$' + change.toFixed(2);
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text
                    }
                },
                y: {
                    grid: {
                        color: colors.grid,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text,
                        callback: function(value) {
                            return '$' + value;
                        }
                    },
                    title: {
                        display: true,
                        text: 'Value per Share',
                        color: colors.text
                    }
                }
            }
        }
    });
}

/**
 * Initialize sensitivity heatmap
 */
function initHeatmap(data) {
    const ctx = document.getElementById('heatmapChart');
    if (!ctx) return;
    
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const colors = isDark ? darkChartColors : chartColors;
    
    // Create matrix data for heatmap
    const matrixData = [];
    const growthRates = data.growthRates || [-5, 0, 5, 10, 15];
    const margins = data.margins || [25, 30, 35, 40, 45];
    
    margins.forEach((margin, i) => {
        growthRates.forEach((growth, j) => {
            matrixData.push({
                x: j,
                y: i,
                v: data.values[i][j] || 100
            });
        });
    });
    
    // Create color scale
    const minValue = Math.min(...matrixData.map(d => d.v));
    const maxValue = Math.max(...matrixData.map(d => d.v));
    
    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Sensitivity Analysis',
                data: matrixData,
                backgroundColor: function(context) {
                    const value = context.raw.v;
                    const normalized = (value - minValue) / (maxValue - minValue);
                    
                    // Create gradient from red to green
                    if (normalized < 0.5) {
                        return `rgba(239, 68, 68, ${0.3 + normalized * 0.7})`;
                    } else {
                        return `rgba(16, 185, 129, ${0.3 + (normalized - 0.5) * 1.4})`;
                    }
                },
                borderColor: colors.grid,
                borderWidth: 1,
                pointRadius: 30,
                pointHoverRadius: 35,
                pointStyle: 'rect'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: isDark ? '#1f2937' : '#ffffff',
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    callbacks: {
                        title: function(context) {
                            const dataPoint = context[0].raw;
                            return `Growth: ${growthRates[dataPoint.x]}%, Margin: ${margins[dataPoint.y]}%`;
                        },
                        label: function(context) {
                            return 'Value: $' + context.raw.v.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'category',
                    labels: growthRates.map(g => g + '%'),
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text
                    },
                    title: {
                        display: true,
                        text: 'Revenue Growth Rate',
                        color: colors.text
                    }
                },
                y: {
                    type: 'category',
                    labels: margins.map(m => m + '%'),
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text
                    },
                    title: {
                        display: true,
                        text: 'Operating Margin',
                        color: colors.text
                    }
                }
            }
        }
    });
}

/**
 * Initialize FCF projection chart
 */
function initFCFChart(data) {
    const ctx = document.getElementById('fcfChart');
    if (!ctx) return;
    
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const colors = isDark ? darkChartColors : chartColors;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.years || ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Terminal'],
            datasets: [{
                label: 'Free Cash Flow',
                data: data.fcf || [],
                backgroundColor: function(context) {
                    const value = context.raw;
                    return value >= 0 ? colors.success + '80' : colors.danger + '80';
                },
                borderColor: function(context) {
                    const value = context.raw;
                    return value >= 0 ? colors.success : colors.danger;
                },
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: colors.text,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: isDark ? '#1f2937' : '#ffffff',
                    titleColor: colors.text,
                    bodyColor: colors.text,
                    borderColor: colors.grid,
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': $' + context.raw.toFixed(1) + 'B';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text
                    }
                },
                y: {
                    grid: {
                        color: colors.grid,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.text,
                        callback: function(value) {
                            return '$' + value + 'B';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Free Cash Flow (Billions)',
                        color: colors.text
                    }
                }
            }
        }
    });
}

/**
 * Update charts when theme changes
 */
function updateChartsTheme() {
    // Destroy and reinitialize all charts with new colors
    Chart.helpers.each(Chart.instances, function(instance) {
        instance.destroy();
    });
    
    // Reinitialize with current theme
    if (window.chartData) {
        if (window.chartData.revenue) initRevenueChart(window.chartData.revenue);
        if (window.chartData.waterfall) initWaterfallChart(window.chartData.waterfall);
        if (window.chartData.heatmap) initHeatmap(window.chartData.heatmap);
        if (window.chartData.fcf) initFCFChart(window.chartData.fcf);
    }
}

/**
 * Export chart as image
 */
function exportChart(chartId, filename) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    
    const url = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = filename || 'chart.png';
    link.href = url;
    link.click();
}

// Export functions for global use
window.initRevenueChart = initRevenueChart;
window.initWaterfallChart = initWaterfallChart;
window.initHeatmap = initHeatmap;
window.initFCFChart = initFCFChart;
window.updateChartsTheme = updateChartsTheme;
window.exportChart = exportChart;