"""``search_help_faqs``: the model's only source for application questions, over the session's corpus."""

from __future__ import annotations

import logging

from livekit.agents import RunContext
from livekit.agents.llm import function_tool
from voice_infra.tool_log import agent_tool_log
from voice_infra.tool_progress import filler_kwargs, filler_line

from livekit_assistant_worker.help_corpus import HelpCorpus, search

logger = logging.getLogger(__name__)

TOOL_NAME = "search_help_faqs"
PROGRESS_LINE = "Let me check the help articles for your question."


async def run_search_help_faqs(context: RunContext, corpus: HelpCorpus, query: str) -> str:
    """Search the corpus with async progress updates until the lookup completes."""
    await context.update(PROGRESS_LINE)
    agent_tool_log(f"TOOL_CALL tool={TOOL_NAME} phase=start query_chars={len(query or '')}")
    try:
        async with context.with_filler(filler_line, **filler_kwargs()):
            formatted, match_count = search(corpus, query, limit=3)
        agent_tool_log(f"TOOL_CALL tool={TOOL_NAME} phase=done match_count={match_count} payload_chars={len(formatted)}")
        return formatted
    except Exception as e:
        agent_tool_log(f"TOOL_CALL tool={TOOL_NAME} phase=error error={e!r}")
        logger.error("Error searching FAQs: %s", e)
        raise Exception("Unable to help user") from e


def build_search_help_faqs_tool(corpus: HelpCorpus):
    async def _search(context: RunContext, query: str) -> str:
        return await run_search_help_faqs(context, corpus, query)

    return function_tool(
        _search,
        name=TOOL_NAME,
        description=(
            "Search the application FAQs by the user's question. Call once per question with a "
            "query string (required). Returns up to 3 matching Q&A pairs; answer only from them, "
            "and if none fit follow the no-match guidance in the result. Use when the user asks "
            "for help or app guidance. NEVER use markdown in spoken responses."
        ),
    )
