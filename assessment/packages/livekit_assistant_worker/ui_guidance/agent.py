"""The Agent used for sessions that can see the screen.

It differs from a plain Agent in one way: pointer tags written inline in the
model's reply are taken out of the text before it is spoken or transcribed, and
the highlight is published as the stream passes the tag.
"""

from __future__ import annotations

from collections.abc import AsyncIterable
from typing import Any

from livekit.agents import Agent, ModelSettings

from .pointer_tags import strip_pointer_tags
from .toolset import ComputerToolset


class GuidanceAgent(Agent):
    """An agent that keeps pointer tags out of the spoken and written reply and acts on them."""

    def __init__(self, *, toolset: ComputerToolset, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._toolset = toolset

    def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings) -> Any:
        """Speak the reply without its tags, placing the pointer as they go by.

        The pointer is published from this node and not from the transcript node,
        because this is the one whose timing the user perceives — and because
        publishing from both would place every highlight twice.
        """
        return Agent.default.tts_node(
            self, strip_pointer_tags(text, self._toolset.point_at), model_settings
        )

    def transcription_node(self, text: AsyncIterable[Any], model_settings: ModelSettings) -> Any:
        """Keep the tags out of the transcript, silently."""
        return Agent.default.transcription_node(self, strip_pointer_tags(text), model_settings)
