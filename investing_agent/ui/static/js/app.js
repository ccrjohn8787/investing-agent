/**
 * Main application JavaScript for investment report UI
 */

// Application state
const AppState = {
    currentSection: 'executive-summary',
    theme: 'light',
    sidebarOpen: false,
    preferences: {},
    shortcuts: {
        '1': 'executive-summary',
        '2': 'key-metrics',
        '3': 'dcf-model',
        '4': 'sensitivity',
        '5': 'financial-analysis',
        '6': 'investment-thesis',
        '7': 'risks',
        '8': 'evidence',
        '9': 'projections',
        't': 'toggleTheme',
        'd': 'toggleSidebar',
        'e': 'exportMenu',
        's': 'search',
        '?': 'help'
    }
};

/**
 * Initialize application
 */
function initializeApp() {
    // Load preferences from localStorage
    loadPreferences();
    
    // Apply saved theme
    applyTheme(AppState.theme);
    
    // Initialize event listeners
    initEventListeners();
    
    // Initialize keyboard shortcuts
    initKeyboardShortcuts();
    
    // Initialize mobile menu
    initMobileMenu();
    
    // Initialize charts if data available
    if (window.reportData) {
        initializeCharts();
    }
    
    // Initialize tooltips
    initTooltips();
    
    // Mark app as initialized
    document.body.classList.add('app-initialized');
}

/**
 * Load user preferences from localStorage
 */
function loadPreferences() {
    try {
        const saved = localStorage.getItem('reportPreferences');
        if (saved) {
            AppState.preferences = JSON.parse(saved);
            AppState.theme = AppState.preferences.theme || 'light';
        }
    } catch (e) {
        console.warn('Failed to load preferences:', e);
    }
}

/**
 * Save user preferences to localStorage
 */
function savePreferences() {
    try {
        AppState.preferences = {
            theme: AppState.theme,
            lastSection: AppState.currentSection,
            sidebarOpen: AppState.sidebarOpen,
            timestamp: new Date().toISOString()
        };
        localStorage.setItem('reportPreferences', JSON.stringify(AppState.preferences));
    } catch (e) {
        console.warn('Failed to save preferences:', e);
    }
}

/**
 * Initialize event listeners
 */
function initEventListeners() {
    // Navigation items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            const sectionId = this.getAttribute('data-section') || 
                           this.getAttribute('onclick')?.match(/showSection\('(.+?)'\)/)?.[1];
            if (sectionId) {
                showSection(sectionId);
            }
        });
    });
    
    // Theme toggle
    const themeBtn = document.querySelector('[onclick="toggleTheme()"]');
    if (themeBtn) {
        themeBtn.removeAttribute('onclick');
        themeBtn.addEventListener('click', toggleTheme);
    }
    
    // Export buttons
    const exportButtons = {
        'exportPDF': exportToPDF,
        'exportExcel': exportToExcel,
        'exportCSV': exportToCSV,
        'exportJSON': exportToJSON
    };
    
    Object.keys(exportButtons).forEach(id => {
        const btn = document.querySelector(`[onclick="${id}()"]`);
        if (btn) {
            btn.removeAttribute('onclick');
            btn.addEventListener('click', exportButtons[id]);
        }
    });
    
    // DCF sliders
    const sliders = ['growth', 'margin', 'wacc', 'terminal'];
    sliders.forEach(name => {
        const slider = document.getElementById(`${name}-slider`);
        if (slider) {
            slider.addEventListener('input', updateDCF);
        }
    });
    
    // Window resize
    window.addEventListener('resize', handleResize);
    
    // Before unload - save preferences
    window.addEventListener('beforeunload', savePreferences);
}

/**
 * Initialize keyboard shortcuts
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ignore if typing in input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const key = e.key.toLowerCase();
        const action = AppState.shortcuts[key];
        
        if (!action) return;
        
        // Check for modifier keys
        if (e.ctrlKey || e.metaKey) {
            // Ctrl/Cmd + key combinations
            switch(key) {
                case 'e':
                    e.preventDefault();
                    showExportMenu();
                    break;
                case 's':
                    e.preventDefault();
                    showSearch();
                    break;
            }
        } else {
            // Regular key press
            if (action === 'toggleTheme') {
                toggleTheme();
            } else if (action === 'toggleSidebar') {
                toggleSidebar();
            } else if (action === 'exportMenu') {
                showExportMenu();
            } else if (action === 'search') {
                showSearch();
            } else if (action === 'help') {
                showHelp();
            } else {
                // Navigate to section
                showSection(action);
            }
        }
    });
}

/**
 * Initialize mobile menu
 */
function initMobileMenu() {
    // Add hamburger menu button if not exists
    if (!document.querySelector('.mobile-menu-btn')) {
        const header = document.querySelector('.header-content');
        if (header) {
            const menuBtn = document.createElement('button');
            menuBtn.className = 'mobile-menu-btn';
            menuBtn.innerHTML = '☰';
            menuBtn.style.cssText = `
                display: none;
                position: fixed;
                top: 1rem;
                left: 1rem;
                z-index: 1001;
                background: var(--primary-color);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 1.5rem;
                cursor: pointer;
            `;
            menuBtn.addEventListener('click', toggleSidebar);
            document.body.appendChild(menuBtn);
        }
    }
    
    // Add overlay for mobile menu
    if (!document.querySelector('.sidebar-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 99;
        `;
        overlay.addEventListener('click', closeSidebar);
        document.body.appendChild(overlay);
    }
}

/**
 * Show specific section
 */
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show selected section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
        AppState.currentSection = sectionId;
        
        // Update nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            const itemSection = item.getAttribute('data-section') || 
                              item.getAttribute('onclick')?.match(/showSection\('(.+?)'\)/)?.[1];
            if (itemSection === sectionId) {
                item.classList.add('active');
            }
        });
        
        // Initialize section-specific features
        initSectionFeatures(sectionId);
        
        // Close mobile sidebar
        if (window.innerWidth <= 1024) {
            closeSidebar();
        }
        
        // Save preference
        savePreferences();
    }
}

/**
 * Initialize section-specific features
 */
function initSectionFeatures(sectionId) {
    switch(sectionId) {
        case 'key-metrics':
            if (!window.revenueChartInitialized) {
                initializeCharts();
                window.revenueChartInitialized = true;
            }
            break;
        case 'dcf-model':
            if (!window.waterfallChartInitialized) {
                initWaterfallChart(getWaterfallData());
                window.waterfallChartInitialized = true;
            }
            break;
        case 'sensitivity':
            if (!window.heatmapInitialized) {
                initHeatmap(getHeatmapData());
                window.heatmapInitialized = true;
            }
            break;
    }
}

/**
 * Toggle theme
 */
function toggleTheme() {
    AppState.theme = AppState.theme === 'dark' ? 'light' : 'dark';
    applyTheme(AppState.theme);
    savePreferences();
    
    // Update charts if they exist
    if (window.updateChartsTheme) {
        window.updateChartsTheme();
    }
}

/**
 * Apply theme
 */
function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    
    // Update theme button icon
    const themeBtn = document.querySelector('.btn:has(☾), .btn:has(☀)') || 
                     document.querySelector('[onclick*="toggleTheme"]');
    if (themeBtn) {
        themeBtn.textContent = theme === 'dark' ? '☀' : '🌙';
    }
}

/**
 * Toggle sidebar
 */
function toggleSidebar() {
    AppState.sidebarOpen = !AppState.sidebarOpen;
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (AppState.sidebarOpen) {
        sidebar.classList.add('open');
        if (overlay) overlay.style.display = 'block';
    } else {
        sidebar.classList.remove('open');
        if (overlay) overlay.style.display = 'none';
    }
}

/**
 * Close sidebar
 */
function closeSidebar() {
    AppState.sidebarOpen = false;
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    sidebar.classList.remove('open');
    if (overlay) overlay.style.display = 'none';
}

/**
 * Handle window resize
 */
function handleResize() {
    // Show/hide mobile menu button
    const menuBtn = document.querySelector('.mobile-menu-btn');
    if (menuBtn) {
        menuBtn.style.display = window.innerWidth <= 1024 ? 'block' : 'none';
    }
    
    // Close sidebar on desktop
    if (window.innerWidth > 1024 && AppState.sidebarOpen) {
        closeSidebar();
    }
}

/**
 * Show export menu
 */
function showExportMenu() {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 400px;">
            <div class="modal-header">
                <h3 class="modal-title">Export Report</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div class="export-options" style="display: grid; gap: 1rem;">
                <button class="btn btn-primary" onclick="exportToPDF(); this.closest('.modal').remove()">
                    📄 Export as PDF
                </button>
                <button class="btn btn-primary" onclick="exportToExcel(); this.closest('.modal').remove()">
                    📊 Export as Excel
                </button>
                <button class="btn btn-primary" onclick="exportToCSV(); this.closest('.modal').remove()">
                    📋 Export as CSV
                </button>
                <button class="btn btn-primary" onclick="exportToJSON(); this.closest('.modal').remove()">
                    📦 Export as JSON
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

/**
 * Show search functionality
 */
function showSearch() {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h3 class="modal-title">Search Report</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div style="margin-top: 1rem;">
                <input type="text" id="search-input" placeholder="Search in report..." 
                       style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); 
                              border-radius: 6px; font-size: 1rem;">
                <div id="search-results" style="margin-top: 1rem; max-height: 400px; overflow-y: auto;"></div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    const searchInput = document.getElementById('search-input');
    searchInput.focus();
    searchInput.addEventListener('input', performSearch);
}

/**
 * Perform search
 */
function performSearch(e) {
    const query = e.target.value.toLowerCase();
    const resultsDiv = document.getElementById('search-results');
    
    if (query.length < 2) {
        resultsDiv.innerHTML = '';
        return;
    }
    
    const results = [];
    const sections = document.querySelectorAll('.section');
    
    sections.forEach(section => {
        const text = section.textContent.toLowerCase();
        if (text.includes(query)) {
            const title = section.querySelector('.section-title')?.textContent || section.id;
            const snippet = getTextSnippet(section.textContent, query);
            results.push({
                sectionId: section.id,
                title: title,
                snippet: snippet
            });
        }
    });
    
    if (results.length > 0) {
        resultsDiv.innerHTML = results.map(r => `
            <div class="search-result" style="padding: 1rem; border-bottom: 1px solid var(--border-color); cursor: pointer;"
                 onclick="showSection('${r.sectionId}'); this.closest('.modal').remove()">
                <strong>${r.title}</strong>
                <div style="color: var(--text-color); opacity: 0.8; font-size: 0.875rem; margin-top: 0.25rem;">
                    ${r.snippet}
                </div>
            </div>
        `).join('');
    } else {
        resultsDiv.innerHTML = '<p style="padding: 1rem; color: var(--text-color); opacity: 0.6;">No results found</p>';
    }
}

/**
 * Get text snippet around search term
 */
function getTextSnippet(text, query) {
    const index = text.toLowerCase().indexOf(query);
    const start = Math.max(0, index - 50);
    const end = Math.min(text.length, index + query.length + 50);
    let snippet = text.substring(start, end);
    
    // Highlight the search term
    const regex = new RegExp(`(${query})`, 'gi');
    snippet = snippet.replace(regex, '<mark>$1</mark>');
    
    return '...' + snippet + '...';
}

/**
 * Show help modal
 */
function showHelp() {
    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h3 class="modal-title">Keyboard Shortcuts</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div style="margin-top: 1rem;">
                <table style="width: 100%;">
                    <tr><td><kbd>1-9</kbd></td><td>Navigate to sections</td></tr>
                    <tr><td><kbd>T</kbd></td><td>Toggle theme</td></tr>
                    <tr><td><kbd>D</kbd></td><td>Toggle sidebar</td></tr>
                    <tr><td><kbd>E</kbd></td><td>Export menu</td></tr>
                    <tr><td><kbd>S</kbd></td><td>Search</td></tr>
                    <tr><td><kbd>?</kbd></td><td>Show this help</td></tr>
                    <tr><td><kbd>Ctrl+E</kbd></td><td>Quick export</td></tr>
                    <tr><td><kbd>Ctrl+S</kbd></td><td>Quick search</td></tr>
                </table>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

/**
 * Initialize tooltips
 */
function initTooltips() {
    // Add tooltips to buttons
    const tooltips = {
        '.evaluation-badge': 'Click to see detailed quality scores',
        '[onclick*="toggleTheme"]': 'Toggle dark/light theme (T)',
        '[onclick*="exportPDF"]': 'Export as PDF (E)',
        '[onclick*="shareReport"]': 'Share report link'
    };
    
    Object.keys(tooltips).forEach(selector => {
        const element = document.querySelector(selector);
        if (element) {
            element.setAttribute('title', tooltips[selector]);
        }
    });
}

/**
 * Initialize charts with real data
 */
function initializeCharts() {
    if (!window.reportData) return;
    
    const data = window.reportData;
    
    // Prepare chart data
    window.chartData = {
        revenue: prepareRevenueData(data),
        waterfall: getWaterfallData(),
        heatmap: getHeatmapData(),
        fcf: prepareFCFData(data)
    };
    
    // Initialize visible charts
    const activeSection = document.querySelector('.section.active');
    if (activeSection) {
        initSectionFeatures(activeSection.id);
    }
}

/**
 * Prepare revenue chart data
 */
function prepareRevenueData(data) {
    const projections = data.projections || [];
    return {
        years: projections.map(p => `Year ${p.year}`),
        revenue: projections.map(p => parseFloat(p.revenue.replace(/[^0-9.-]/g, '')) / 1000),
        margin: projections.map(p => parseFloat(p.margin))
    };
}

/**
 * Prepare FCF chart data
 */
function prepareFCFData(data) {
    const projections = data.projections || [];
    return {
        years: projections.map(p => `Year ${p.year}`),
        fcf: projections.map(p => parseFloat(p.fcff.replace(/[^0-9.-]/g, '')) / 1000)
    };
}

/**
 * Get waterfall chart data
 */
function getWaterfallData() {
    if (!window.reportData) return { baseValue: 100, changes: [], labels: [] };
    
    const data = window.reportData;
    const baseValue = data.valuation.fair_value;
    
    // Simulate impacts (in production, calculate from actual changes)
    return {
        baseValue: baseValue,
        changes: [5, 8, -3, 2],
        labels: ['Base', 'Growth', 'Margin', 'WACC', 'Terminal', 'Final']
    };
}

/**
 * Get heatmap data
 */
function getHeatmapData() {
    if (!window.reportData) return { growthRates: [], margins: [], values: [] };
    
    // Generate sensitivity matrix
    const growthRates = [-5, 0, 5, 10, 15];
    const margins = [25, 30, 35, 40, 45];
    const baseValue = window.reportData.valuation.fair_value;
    
    const values = margins.map(m => 
        growthRates.map(g => 
            baseValue * (1 + (g * 0.02 + (m - 35) * 0.03))
        )
    );
    
    return { growthRates, margins, values };
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

// Export main functions for global use
window.showSection = showSection;
window.toggleTheme = toggleTheme;
window.toggleSidebar = toggleSidebar;
window.updateDCF = updateDCF;
window.resetAssumptions = resetAssumptions;
window.showScoreDetails = showScoreDetails;
window.closeScoreDetails = closeScoreDetails;
window.sortTable = sortTable;
window.shareReport = shareReport;