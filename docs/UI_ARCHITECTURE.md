# UI Architecture & Design Document

## Overview

This document describes the architecture and design for the Interactive Investment Report UI, emphasizing separation of concerns between the UI presentation layer and the data/logic layer.

## Design Principles

### 1. Separation of Concerns
- **UI Layer**: Purely presentational, handles display and user interactions
- **Data Layer**: Business logic, valuation calculations, and data processing
- **Interface Contract**: Well-defined JSON/API boundaries between layers

### 2. Progressive Enhancement
- **Base**: Functional HTML that works without JavaScript
- **Enhanced**: Interactive features added via JavaScript
- **Fallback**: Graceful degradation when features unavailable

### 3. Self-Contained Reports
- **Single File**: Each report is a standalone HTML file
- **Embedded Assets**: CSS, JS, and data included inline
- **Offline Ready**: No external dependencies required

## Architecture Layers

### Data Layer (Python)
```
investing_agent/
├── agents/           # Business logic agents
├── kernels/          # Valuation calculations
├── schemas/          # Data models
└── connectors/       # External data sources
```

### Interface Layer (JSON)
```json
{
  "metadata": {
    "ticker": "AAPL",
    "company": "Apple Inc.",
    "generated": "2025-01-09T18:00:00Z",
    "evaluation_score": 7.5
  },
  "valuation": {
    "fair_value": 178.50,
    "current_price": 165.00,
    "upside": 0.082
  },
  "financial_data": {...},
  "narrative_sections": {...},
  "evidence": {...},
  "charts_data": {...}
}
```

### Presentation Layer (HTML/CSS/JS)
```
ui/
├── templates/        # HTML templates
├── static/
│   ├── css/         # Stylesheets
│   └── js/          # JavaScript modules
└── builders/        # HTML generation
```

## Component Architecture

### 1. Report Builder (Python)
```python
class InteractiveReportBuilder:
    """Generates interactive HTML reports from data."""
    
    def build(self, data: ReportData) -> str:
        # 1. Extract data from valuation/narrative
        # 2. Serialize to JSON
        # 3. Inject into HTML template
        # 4. Return self-contained HTML
```

### 2. Data Model (JSON Schema)
```typescript
interface ReportData {
  // Core valuation data
  valuation: {
    fairValue: number;
    pvExplicit: number;
    pvTerminal: number;
    assumptions: AssumptionSet;
  };
  
  // Time series for charts
  projections: {
    years: number[];
    revenue: number[];
    fcff: number[];
    growth: number[];
  };
  
  // Narrative sections
  narrative: {
    executiveSummary: string;
    investmentThesis: string;
    riskAnalysis: string;
  };
  
  // Evaluation metrics
  evaluation: {
    overallScore: number;
    dimensions: DimensionScore[];
    timestamp: string;
  };
}
```

### 3. UI Components (JavaScript)

#### DCF Model Viewer
```javascript
class DCFModelViewer {
  constructor(data, container) {
    this.originalData = data;
    this.currentData = {...data};
    this.container = container;
  }
  
  updateAssumption(key, value) {
    // Update local data
    this.currentData.assumptions[key] = value;
    // Recalculate valuation
    this.recalculate();
    // Update display
    this.render();
  }
  
  recalculate() {
    // Client-side DCF calculation
    // Mirrors Python valuation logic
  }
}
```

#### Evaluation Score Display
```javascript
class EvaluationScoreWidget {
  constructor(scoreData, container) {
    this.score = scoreData.overallScore;
    this.dimensions = scoreData.dimensions;
    this.container = container;
  }
  
  render() {
    // Display overall score badge
    // Show dimensional breakdown
    // Color coding by score range
  }
}
```

## Data Flow

### 1. Report Generation
```
Python Backend → JSON Data → HTML Template → Interactive Report
```

### 2. User Interaction
```
User Input → JavaScript → Local Calculation → UI Update
                ↓
         Export/Save → JSON/PDF/Excel
```

### 3. Evaluation Integration
```
Report Generation → Evaluation Engine → Score Data
                           ↓
                    Embed in Report → Display Widget
```

## Implementation Strategy

### Phase 1: Foundation
1. Define JSON schema for report data
2. Create HTML template structure
3. Implement CSS Grid layout
4. Add basic JavaScript framework

### Phase 2: Core Features
1. Interactive tables with sorting
2. Chart.js integration for visualizations
3. DCF model playground
4. Evaluation score display

### Phase 3: Advanced Features
1. Scenario comparison tool
2. Evidence citation viewer
3. Export functionality
4. Dark mode support

### Phase 4: Optimization
1. Performance tuning
2. Cross-browser testing
3. Print stylesheet
4. Accessibility improvements

## Evaluation Score Integration

### Display Locations
1. **Header Badge**: Prominent score display with color coding
2. **Detailed Panel**: Expandable section with dimensional breakdown
3. **Historical View**: Score trends over multiple report generations
4. **Comparison Mode**: Side-by-side score comparison

### Score Visualization
```
Overall: 7.5/10 [Good]
├── Strategic Narrative: 8.0 ████████░░
├── Analytical Rigor: 7.0 ███████░░░
├── Industry Context: 7.5 ████████░░
├── Professional: 8.0 ████████░░
└── Citations: 7.0 ███████░░░
```

### Color Scheme
- **9-10**: Green (Exceptional)
- **7-8**: Blue (Good)
- **5-6**: Yellow (Acceptable)
- **3-4**: Orange (Poor)
- **0-2**: Red (Inadequate)

## File Structure

### Templates
```html
<!-- report.html -->
<!DOCTYPE html>
<html>
<head>
  <title>{{company}} Investment Report</title>
  <style>/* Embedded CSS */</style>
</head>
<body>
  <div id="report-container">
    <!-- Navigation -->
    <nav id="sidebar">...</nav>
    
    <!-- Main Content -->
    <main id="content">
      <!-- Evaluation Score -->
      <div id="evaluation-score"></div>
      
      <!-- DCF Model -->
      <div id="dcf-model"></div>
      
      <!-- Narratives -->
      <div id="narratives"></div>
    </main>
  </div>
  
  <script>
    // Embedded data
    const reportData = {{json_data}};
    
    // Initialize components
    new ReportViewer(reportData);
  </script>
</body>
</html>
```

### JavaScript Modules
```javascript
// app.js - Main application
class ReportViewer {
  constructor(data) {
    this.data = data;
    this.initComponents();
  }
}

// dcf.js - DCF model interactions
class DCFModel {
  calculate(inputs) {
    // Mirror Python valuation logic
  }
}

// evaluation.js - Score display
class EvaluationDisplay {
  render(scores) {
    // Create visual representation
  }
}

// charts.js - Chart.js wrappers
class ChartManager {
  createChart(type, data, options) {
    // Initialize Chart.js
  }
}
```

## Testing Strategy

### Unit Tests
- JavaScript calculation logic
- Component rendering
- Data transformation

### Integration Tests
- Python to HTML generation
- Data flow validation
- Export functionality

### Visual Tests
- Cross-browser rendering
- Responsive breakpoints
- Print layout

## Performance Considerations

### Optimization Targets
- Initial load: < 2 seconds
- Interaction response: < 100ms
- Export generation: < 5 seconds

### Techniques
- Lazy loading for charts
- Virtual scrolling for tables
- Web Workers for calculations
- Compressed inline assets

## Security Considerations

### Data Sanitization
- HTML escape all user inputs
- Validate JSON schema
- Sanitize export filenames

### Content Security
- No external dependencies
- No inline event handlers
- Strict CSP headers if served

## Future Enhancements

### Planned Features
1. Real-time collaboration
2. Cloud storage integration
3. API for programmatic access
4. Mobile native apps

### Technology Evolution
1. Consider React/Vue for complex interactions
2. WebAssembly for performance-critical calculations
3. Progressive Web App capabilities
4. Server-side rendering option

## Conclusion

This architecture ensures clean separation between UI and business logic, enabling independent evolution of both layers while maintaining a stable interface contract. The design prioritizes user experience, performance, and maintainability while delivering professional-grade investment research tools.