"""The only prompt text the worker owns: how it reports its own tool state to the model.

Session instructions, greetings, FAQ content and speech-to-speech
instructions are the backend's and arrive rendered in the bootstrap.
"""

from .navigation import navigation_mode_prompt

__all__ = ["navigation_mode_prompt"]
