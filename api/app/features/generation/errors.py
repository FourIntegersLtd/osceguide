"""The refusals an AI content generation call can raise."""

from app.core.errors import AppError


class GenerationUnavailable(AppError):
    """Raised when no OpenAI API key is configured, so a platform admin cannot generate content here."""

    code = "generation_unavailable"
    default_message = "Content generation is not configured on this environment"


class GenerationEmpty(AppError):
    """Raised when the model answered but wrote none of what was asked for, e.g. a deck with no slides,
    so an empty draft is never saved as if it had been written."""

    status = 422
    code = "generation_empty"
    default_message = "The model wrote no slides. Phrase the brief as the deck to write and try again."
