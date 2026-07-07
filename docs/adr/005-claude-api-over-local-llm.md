# ADR 005: Claude API over Local LLM for AI Chat

## Status

Accepted (2026-07-07)

## Context

The dashboard includes an AI chat assistant that answers questions about pipeline health, data quality, and transaction trends. Two approaches for the LLM backend:

1. Claude API (Anthropic) — proprietary, cloud-hosted, paid per-token
2. Local LLM (ollama, llama.cpp, vLLM) — open-source, self-hosted, GPU-dependent

The chat assistant needs to:
- Answer questions about specific pipeline metrics and data quality
- Provide actionable recommendations based on current pipeline state
- Respond in under 5 seconds
- Understand the pipeline architecture and BigQuery schema

## Decision

Use the Claude API via the official Anthropic Python SDK.

## Consequences

### Positive
- Zero infrastructure — no GPU required, no model hosting, no vLLM server to maintain
- Best-in-class instruction following — Claude reliably stays within the system prompt guardrails
- Fast responses — Claude Sonnet 4 responds in 1-3 seconds for short answers
- No hardware dependency — works on any server that can make HTTPS requests
- Simple deployment — the Docker container needs only an API key environment variable

### Negative
- Ongoing cost — Claude API costs $3/M input tokens and $15/M output tokens
- Internet dependency — cannot answer questions without API access
- Data privacy — pipeline data is sent to Anthropic's servers (mitigated by prompt design that sends only aggregate metrics, not raw row-level data)
- API key management — the key must be securely stored and rotated

### Mitigations
- The chat is designed as a widget, not the primary interface — users can answer most questions by looking at the charts
- The system prompt sends only aggregate statistics and schema descriptions, not raw row-level data — no PII or sensitive data is exposed
- The API key is configured via environment variable (CLAUDE_API_KEY) and never hardcoded in the codebase
- Estimated cost: ~$0.10-0.50 per month for typical dashboard usage (10-50 questions per week)
- If the API key is not configured, the chat widget shows a helpful message and gracefully degrades

## Alternatives Considered

### Ollama (local LLM)
- **Pros**: Free, private, no API dependency, works offline
- **Cons**: Requires GPU (for acceptable response times), model must be downloaded and updated, smaller models have worse instruction-following, additional Docker container or host dependency
- **Rejected because**: The dashboard is deployed as a single Docker container on the cheapest Cloud Run tier (or free-tier VM). Adding a GPU-dependent local LLM doubles deployment complexity and cost. For a portfolio project, the Claude API proxy pattern is more impressive to interviewers than a local 7B model running on CPU.

### No AI assistant
- **Pros**: Simplest possible architecture, zero cost, no API dependency
- **Cons**: Less impressive as a portfolio project, loses the opportunity to demonstrate LLM integration
- **Rejected because**: The AI chat widget is a key differentiator for the portfolio. It shows the ability to integrate LLMs with structured data systems — a core skill for modern data engineering roles.
