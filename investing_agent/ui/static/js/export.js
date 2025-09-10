/**
 * Export functionality for investment reports
 */

/**
 * Export report data to CSV format
 */
function exportToCSV() {
    if (!window.reportData) {
        alert('No data available to export');
        return;
    }
    
    const data = window.reportData;
    let csv = [];
    
    // Header section
    csv.push(['Company Information']);
    csv.push(['Company', data.company]);
    csv.push(['Ticker', data.ticker]);
    csv.push(['Report Date', new Date().toISOString().split('T')[0]]);
    csv.push([]);
    
    // Valuation summary
    csv.push(['Valuation Summary']);
    csv.push(['Fair Value', data.valuation.fair_value]);
    csv.push(['Current Price', data.current_price]);
    csv.push(['Upside', data.upside + '%']);
    csv.push(['PV Explicit', data.valuation.pv_explicit]);
    csv.push(['PV Terminal', data.valuation.pv_terminal]);
    csv.push([]);
    
    // Key assumptions
    csv.push(['Key Assumptions']);
    csv.push(['Revenue Growth', data.assumptions.growth + '%']);
    csv.push(['Operating Margin', data.assumptions.margin + '%']);
    csv.push(['WACC', data.assumptions.wacc + '%']);
    csv.push(['Terminal Growth', data.assumptions.terminal_growth + '%']);
    csv.push([]);
    
    // Projections table
    csv.push(['Financial Projections']);
    csv.push(['Year', 'Revenue', 'Growth %', 'Margin %', 'FCFF', 'PV(FCFF)']);
    
    if (data.projections) {
        data.projections.forEach(row => {
            csv.push([
                row.year,
                row.revenue,
                row.growth,
                row.margin,
                row.fcff,
                row.pv
            ]);
        });
    }
    csv.push([]);
    
    // Evaluation scores
    if (data.evaluation) {
        csv.push(['Quality Evaluation']);
        csv.push(['Overall Score', data.evaluation.overall_score + '/10']);
        if (data.evaluation.dimensions) {
            data.evaluation.dimensions.forEach(dim => {
                csv.push([dim.name, dim.score + '/10']);
            });
        }
    }
    
    // Convert to CSV string
    const csvString = csv.map(row => 
        row.map(cell => {
            // Escape quotes and wrap in quotes if contains comma
            const cellStr = String(cell || '');
            if (cellStr.includes(',') || cellStr.includes('"')) {
                return '"' + cellStr.replace(/"/g, '""') + '"';
            }
            return cellStr;
        }).join(',')
    ).join('\n');
    
    // Download file
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${data.ticker}_investment_report.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Export report data to Excel format (using XLSX library if available)
 */
function exportToExcel() {
    if (typeof XLSX === 'undefined') {
        // Fallback to CSV if XLSX library not loaded
        console.warn('XLSX library not found, falling back to CSV export');
        exportToCSV();
        return;
    }
    
    if (!window.reportData) {
        alert('No data available to export');
        return;
    }
    
    const data = window.reportData;
    const wb = XLSX.utils.book_new();
    
    // Summary sheet
    const summaryData = [
        ['Company Information'],
        ['Company', data.company],
        ['Ticker', data.ticker],
        ['Report Date', new Date().toISOString().split('T')[0]],
        [],
        ['Valuation Summary'],
        ['Fair Value', data.valuation.fair_value],
        ['Current Price', data.current_price],
        ['Upside', data.upside],
        ['PV Explicit', data.valuation.pv_explicit],
        ['PV Terminal', data.valuation.pv_terminal]
    ];
    
    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Summary');
    
    // Assumptions sheet
    const assumptionsData = [
        ['Key Assumptions'],
        ['Parameter', 'Value'],
        ['Revenue Growth', data.assumptions.growth],
        ['Operating Margin', data.assumptions.margin],
        ['WACC', data.assumptions.wacc],
        ['Terminal Growth', data.assumptions.terminal_growth]
    ];
    
    const assumptionsSheet = XLSX.utils.aoa_to_sheet(assumptionsData);
    XLSX.utils.book_append_sheet(wb, assumptionsSheet, 'Assumptions');
    
    // Projections sheet
    const projectionsData = [
        ['Year', 'Revenue', 'Growth %', 'Margin %', 'FCFF', 'PV(FCFF)']
    ];
    
    if (data.projections) {
        data.projections.forEach(row => {
            projectionsData.push([
                row.year,
                row.revenue,
                parseFloat(row.growth),
                parseFloat(row.margin),
                row.fcff,
                row.pv
            ]);
        });
    }
    
    const projectionsSheet = XLSX.utils.aoa_to_sheet(projectionsData);
    XLSX.utils.book_append_sheet(wb, projectionsSheet, 'Projections');
    
    // Evaluation sheet
    if (data.evaluation) {
        const evalData = [
            ['Quality Evaluation'],
            ['Overall Score', data.evaluation.overall_score],
            [],
            ['Dimension', 'Score']
        ];
        
        if (data.evaluation.dimensions) {
            data.evaluation.dimensions.forEach(dim => {
                evalData.push([dim.name, dim.score]);
            });
        }
        
        const evalSheet = XLSX.utils.aoa_to_sheet(evalData);
        XLSX.utils.book_append_sheet(wb, evalSheet, 'Evaluation');
    }
    
    // Save file
    XLSX.writeFile(wb, `${data.ticker}_investment_report.xlsx`);
}

/**
 * Export report as PDF (print-friendly version)
 */
function exportToPDF() {
    // Store current state
    const currentView = document.querySelector('.section.active').id;
    
    // Show all sections for printing
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('print-active');
    });
    
    // Add print class to body
    document.body.classList.add('printing');
    
    // Trigger print dialog
    window.print();
    
    // Restore state after a delay
    setTimeout(() => {
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('print-active');
        });
        document.body.classList.remove('printing');
        
        // Restore active section
        showSection(currentView);
    }, 100);
}

/**
 * Export specific table to CSV
 */
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) {
        console.error('Table not found:', tableId);
        return;
    }
    
    const rows = [];
    const tableRows = table.querySelectorAll('tr');
    
    tableRows.forEach(row => {
        const cols = [];
        const cells = row.querySelectorAll('td, th');
        cells.forEach(cell => {
            cols.push(cell.textContent.trim());
        });
        rows.push(cols);
    });
    
    // Convert to CSV
    const csvString = rows.map(row => 
        row.map(cell => {
            // Escape quotes and wrap in quotes if contains comma
            if (cell.includes(',') || cell.includes('"')) {
                return '"' + cell.replace(/"/g, '""') + '"';
            }
            return cell;
        }).join(',')
    ).join('\n');
    
    // Download
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename || 'table_export.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Export report data as JSON
 */
function exportToJSON() {
    if (!window.reportData) {
        alert('No data available to export');
        return;
    }
    
    const jsonString = JSON.stringify(window.reportData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${window.reportData.ticker}_report_data.json`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Copy report link to clipboard
 */
function copyReportLink() {
    const url = window.location.href;
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
            showNotification('Report link copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
            fallbackCopy(url);
        });
    } else {
        fallbackCopy(url);
    }
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopy(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.width = '2em';
    textArea.style.height = '2em';
    textArea.style.padding = '0';
    textArea.style.border = 'none';
    textArea.style.outline = 'none';
    textArea.style.boxShadow = 'none';
    textArea.style.background = 'transparent';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        const msg = successful ? 'Report link copied!' : 'Failed to copy';
        showNotification(msg);
    } catch (err) {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy link');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Show notification message
 */
function showNotification(message, type = 'success') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        border-radius: 6px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation styles if not present
if (!document.getElementById('export-animations')) {
    const style = document.createElement('style');
    style.id = 'export-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .printing .sidebar,
        .printing .header-actions,
        .printing .btn,
        .printing .modal {
            display: none !important;
        }
        
        .printing .main-content {
            margin-left: 0 !important;
        }
        
        .printing .section {
            display: none !important;
        }
        
        .printing .section.print-active {
            display: block !important;
            page-break-after: always;
        }
        
        @media print {
            .sidebar,
            .header-actions,
            .btn,
            .modal {
                display: none !important;
            }
            
            .main-content {
                margin-left: 0 !important;
            }
            
            .section {
                display: none !important;
            }
            
            .section.print-active {
                display: block !important;
                page-break-after: always;
            }
        }
    `;
    document.head.appendChild(style);
}

// Export functions for global use
window.exportToCSV = exportToCSV;
window.exportToExcel = exportToExcel;
window.exportToPDF = exportToPDF;
window.exportToJSON = exportToJSON;
window.exportTableToCSV = exportTableToCSV;
window.copyReportLink = copyReportLink;
window.showNotification = showNotification;