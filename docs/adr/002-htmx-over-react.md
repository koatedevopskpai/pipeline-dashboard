# ADR 002: HTMX over React for Interactive UI

## Status

Accepted (2026-07-07)

## Context

The dashboard needs interactive features: form submissions that update charts, partial page reloads for sections, and loading indicators during BigQuery queries. The decision is between a JavaScript framework (React, Vue, Svelte) and HTMX.

HTMX is a small JavaScript library that extends HTML with attributes for making AJAX requests, triggering events, and swapping DOM elements. It replaces the need for a full JavaScript framework when the backend renders HTML.

React would require:
- A build tool (Vite, Webpack)
- JavaScript bundle with the React runtime
- API endpoints returning JSON instead of HTML
- State management for coordinating chart data across components

HTMX requires:
- A single `<script>` tag in the base template
- Backend endpoints that return HTML partials
- No build step, no bundler, no npm dependencies

## Decision

Use HTMX for all interactive UI, served from the same Django views that render the initial page load.

## Consequences

### Positive
- No JavaScript build tooling — zero npm dependencies, zero bundler configuration
- Django views serve both initial HTML and HTMX partials — single code path for each feature
- Simpler debugging — every network response is readable HTML, not JSON that must be parsed by JavaScript
- Smaller page weight — HTMX is ~14KB minified vs React+Vue+Svelte at 30-100KB+
- Works with Django's CSRF protection out of the box

### Negative
- Less suitable for highly interactive UIs with complex client-side state (drag-and-drop, real-time collaborative editing)
- HTMX's hx-vals for inline data binding is less ergonomic than React's state management
- Fewer developers have HTMX experience than React — marginally harder to hire for

### Mitigations
- The dashboard's interactivity is limited to form submissions and chart filtering — no client-side state management needed
- Any future complex interactive components (e.g., drag-and-drop pipeline builder) can use a small Alpine.js integration alongside HTMX
- HTMX has excellent documentation and a growing community — the learning curve is measured in hours, not weeks

## Alternatives Considered

### Alpine.js
- **Pros**: Similar philosophy to HTMX (HTML-first, minimal JavaScript), good for component-level interactivity
- **Cons**: Less suited for server-driven interactions (form submissions, partial page swaps)
- **Used alongside**: Alpine.js is a complement to HTMX, not a replacement. If client-side interactivity is needed later, Alpine.js can be added without conflict.

### Turbo (Hotwire)
- **Pros**: Rails-native, similar approach to HTMX
- **Cons**: Python ecosystem has less community support for Hotwire patterns
- **Rejected because**: HTMX is framework-agnostic and has better Django documentation
