"""
Chat views — AI-powered pipeline assistant.

Architecture decision: Single view rendering both the page and HTMX partials.

Why: The chat page is a single template with HTMX-driven question/answer
interaction. When the user submits a question via the form, HTMX sends a POST
to this view and swaps in the answer partial. The same view handles both GET
(initial page load) and POST (question submission), keeping the logic in one
place rather than splitting across a form view and a partial view.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .services import claude_client


def index(request: HttpRequest) -> HttpResponse:
    """
    Chat page — ask questions about the pipeline and get AI-powered answers.

    GET: Renders the chat page with an empty state.
    POST: Sends the question to Claude and returns the answer as a partial.
    """
    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if not question:
            return render(request, "chat/partials/answer.html", {
                "error": "Please enter a question.",
            })

        result = claude_client.get_answer(
            question=question,
            api_key=settings.CLAUDE_API_KEY,
            model=settings.CLAUDE_MODEL,
        )

        return render(request, "chat/partials/answer.html", {
            "question": question,
            "result": result,
        })

    return render(request, "chat/index.html", {
        "claude_configured": bool(settings.CLAUDE_API_KEY),
    })
