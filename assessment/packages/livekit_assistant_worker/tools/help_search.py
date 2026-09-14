"""``search_help_faqs``: the only source of truth for application questions."""

from __future__ import annotations

import logging

from livekit.agents import RunContext
from livekit.agents.llm import function_tool
from voice_infra.tool_log import agent_tool_log
from voice_infra.tool_progress import filler_kwargs, filler_line

from livekit_assistant_worker.faq import search_common_queries

logger = logging.getLogger(__name__)


async def run_search_help_faqs(context: RunContext, query: str) -> str:
    """Search FAQs with async progress updates until the lookup completes."""
    await context.update("Let me check the help articles for your question.")
    agent_tool_log(f"TOOL_CALL tool=search_help_faqs phase=start query_chars={len(query or '')}")
    try:
        async with context.with_filler(filler_line, **filler_kwargs()):
            formatted, match_count = search_common_queries(query, limit=3)
        agent_tool_log(f"TOOL_CALL tool=search_help_faqs phase=done match_count={match_count} payload_chars={len(formatted)}")
        return formatted
    except Exception as e:
        agent_tool_log(f"TOOL_CALL tool=search_help_faqs phase=error error={e!r}")
        logger.error("Error searching FAQs: %s", e)
        raise Exception("Unable to help user") from e


@function_tool(
    name="search_help_faqs",
    description=(
        "Search app FAQs by the user's question. Call once per question with a query "
        "string (required). Returns up to 3 matching Q&A pairs. Use when the user asks "
        "for help or app guidance. NEVER use markdown in spoken responses."
    ),
)
async def search_help_faqs(context: RunContext, query: str) -> str:
    """
    Search the app FAQ for answers matching the user's question.

    You MUST call this with the user's question (or a close paraphrase) when they ask
    for help, are confused about the app, or ask a non-clinical question.
    Returns up to 3 matching FAQ entries. Do NOT call without a query string.

    If no FAQ matches, tell the user to use Contact Us in the left navigation bar.

    CRITICAL TTS FORMATTING RULES - FOLLOW STRICTLY:
    - NEVER use asterisks (**) for bold text
    - NEVER use underscores (_) for emphasis
    - NEVER use hashtags (#) for headings
    - NEVER use dashes (-) for bullet points
    - Write everything in plain conversational text
    - Speak naturally as if talking to someone in person
    """
    return await run_search_help_faqs(context, query)
