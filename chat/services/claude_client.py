"""
Claude API client — provides natural language interface to pipeline data.

Architecture decision: Anthropic SDK over raw HTTP POST to API endpoint.

Why: The SDK handles authentication, retry logic with exponential backoff,
rate limiting, streaming response parsing, and token counting. Reimplementing
these features against the raw API would add ~200 lines of error-prone code
with zero benefit. The SDK is the recommended integration path.

Architecture decision: Stateless chat over session-based conversation history.

Why: For a dashboard widget, the chat should answer questions about the
current pipeline state. Full conversation history with context window
management is a feature for a dedicated chat product, not a dashboard
widget. Each question is self-contained with pipeline context injected
as the system prompt.

Architecture decision: Graceful degradation when API key is missing.

Why: The dashboard should work and look complete even without Claude
integration. If no API key is configured, the chat input is hidden and a
helpful message points the user to configure it. This avoids a broken
UI element that frustrates users.
"""
from __future__ import annotations

import logging
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


def _build_system_prompt() -> str:
    """
    Build the system prompt that grounds Claude in the pipeline context.

    Architecture decision: Generated system prompt over hardcoded string.

    Why: The system prompt includes current pandas/analytics context that
    changes as the pipeline evolves. A generated prompt can be updated by
    modifying the BigQuery views without touching the chat code.
    """
    return (
        "You are a data pipeline assistant. You help users understand the "
        "health and performance of their GCP-native data pipeline.\n\n"
        "You can answer questions about:\n"
        "- Pipeline health and recent run status\n"
        "- Data quality metrics (valid rows, errors, duplicates)\n"
        "- Daily transaction volumes and trends\n"
        "- Category and regional spending breakdowns\n"
        "- BigQuery table schemas and partitioning\n\n"
        "Guidelines:\n"
        "- Be concise. Provide specific numbers when possible.\n"
        "- If you don't know something, say so — do not hallucinate.\n"
        "- Suggest actions: 'You could investigate by checking the\n"
        "  ingestion_errors table for recent failures.'\n"
        "- Reference the pipeline architecture: Cloud Storage triggers\n"
        "  Cloud Function → BigQuery staging → SQL transforms → analytics.\n"
        "- Keep responses under 300 words unless the user asks for detail."
    )


def get_answer(question: str, api_key: str, model: str = "claude-sonnet-4-20250514") -> dict[str, Any]:
    """
    Send a question to Claude and return the answer.

    Args:
        question: The user's question about the pipeline.
        api_key: Claude API key from settings.
        model: Claude model to use.

    Returns:
        Dict with "answer" and "model" keys, or "error" key on failure.
    """
    if not api_key:
        logger.warning("Claude API key not configured — cannot answer questions")
        return {
            "error": "Claude API key not configured. "
                     "Set the CLAUDE_API_KEY environment variable to enable AI chat.",
        }

    try:
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_build_system_prompt(),
            messages=[
                {"role": "user", "content": question},
            ],
        )

        answer_text = ""
        for block in response.content:
            if block.type == "text":
                answer_text += block.text

        return {
            "answer": answer_text.strip(),
            "model": model,
        }

    except Exception as e:
        logger.exception("Claude API call failed")
        return {"error": f"Failed to get answer from Claude: {str(e)}"}
