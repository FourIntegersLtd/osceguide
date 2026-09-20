from app.core.errors import AppError


class GenerationUnavailable(AppError):
    code = "generation_unavailable"
    default_message = "Content generation is not configured on this environment"
