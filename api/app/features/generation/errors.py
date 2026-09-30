"""The one refusal an AI content generation call can raise."""

from app.core.errors import AppError


class GenerationUnavailable(AppError):
    """Raised when no OpenAI API key is configured, so a platform admin cannot generate content here."""

    code = "generation_unavailable"
    default_message = "Content generation is not configured on this environment"
