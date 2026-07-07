# ADR 003: Chart.js CDN over npm Bundles

## Status

Accepted (2026-07-07)

## Context

The dashboard displays data visualisations: bar charts for daily transaction volumes, pie charts for category breakdowns, line charts for trends over time. The charting library choice affects page weight, loading time, and rendering performance.

Chart.js is a popular open-source charting library that renders on HTML5 Canvas. It supports the chart types needed (bar, line, pie, doughnut) and is relatively lightweight.

Options for including Chart.js:
1. CDN link in the base HTML template
2. npm package bundled with a JavaScript build tool
3. npm package served as a static file via Django's static file system

## Decision

Load Chart.js from a CDN via a `<script>` tag in the base HTML template.

## Consequences

### Positive
- Zero build tooling — no npm install, no Webpack config, no package.json
- Automatic CDN caching — Chart.js is loaded from the browser cache on subsequent page loads
- Simpler deployment — no static file build step in the Docker image
- The CDN version can be pinned to a specific release for reproducibility

### Negative
- Requires internet access to load charts — no offline rendering
- CDN outage would break chart rendering (mitigated by browser caching)
- No tree-shaking — the full Chart.js library is loaded even if only bar charts are used
- Harder to version-control — the dependency is implicit in the template rather than explicit in package.json

### Mitigations
- The dashboard is designed as an always-online tool — offline rendering is not a requirement
- Chart.js 4.x is loaded from the jsDelivr CDN, which has 99.9%+ uptime and global CDN distribution
- If offline rendering becomes a requirement, Chart.js can be downloaded and served as a Django static file without changing any chart code
- Chart.js 4.x gzipped is ~70KB — acceptable for a dashboard that is not loaded on mobile connections

## Alternatives Considered

### Plotly
- **Pros**: Interactive charts (zoom, pan, hover details), excellent for financial/time-series data
- **Cons**: Much larger bundle (~2MB), heavier rendering overhead, requires more JavaScript for configuration
- **Rejected because**: The dashboard needs simple, clean visualisations. Plotly's interactivity is overkill for daily volume and category breakdown charts.

### D3.js
- **Pros**: Unlimited customisation, most performant for large datasets, full control over visual output
- **Cons**: Significantly more verbose — a simple bar chart requires 50+ lines of D3 code vs 10 lines in Chart.js
- **Rejected because**: The dashboard's charting needs are standard (bar, line, pie). D3 is better suited for novel visualisations or dashboards with millions of data points.

### ApexCharts
- **Pros**: Modern, interactive, good-looking default themes, responsive
- **Cons**: Larger bundle than Chart.js, fewer community resources for troubleshooting
- **Rejected because**: Chart.js has been the most widely adopted charting library for the longest time, meaning more community support and more examples online.
