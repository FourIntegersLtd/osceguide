"""Reading a CV's text into sections, with a model.

The one call this slice makes to a model, kept apart from the use cases so
`service.py` reads as use cases. Structured outputs rather than JSON mode: the
response is held to `schemas.StructuredCv`, the same type the API returns, so
what is stored is what was asked for and a malformed answer is a parse failure
rather than a guess.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.cv.schemas import StructuredCv

log = get_logger(__name__)

# A CV is a short, well-structured document; the small model reads it as well
# as a large one and costs less.
CV_MODEL = "gpt-4o-mini"
PARSE_TIMEOUT_SEC = 240

SYSTEM_PROMPT = (
    "Extract CV data into these sections: summary (career overview), experience "
    "(clinical roles), education (degrees, training), research (projects, interests), "
    "publications (papers, presentations), audits (QIP projects), teaching (educational "
    "roles), leadership (management positions), achievements (awards, recognition), "
    "skills (clinical competencies), grants (funding received), courses (professional "
    "development). Be concise. Leave a section null when the CV has nothing for it."
)


async def extract_structured(text: str, *, settings: Settings) -> tuple[StructuredCv | None, str]:
    """Return `(parsed, error_message)`, never both empty and never both set.

    No API key is an error string rather than an exception: the job records it
    on the row so the person sees why their CV did not read, instead of it
    sitting in `processing` forever.
    """
    if not settings.openai_api_key.strip():
        return None, "OpenAI is not configured (set OPENAI_API_KEY)"

    from openai import AsyncOpenAI

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.beta.chat.completions.parse(
            model=CV_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyse this CV:\n\n{text}"},
            ],
            response_format=StructuredCv,
            timeout=PARSE_TIMEOUT_SEC,
        )
    except Exception as exc:  # noqa: BLE001 - any model failure becomes the row's error
        log.warning("cv extraction failed", error=str(exc))
        return None, str(exc)

    parsed = response.choices[0].message.parsed
    if parsed is None:
        refusal = response.choices[0].message.refusal
        return None, f"Structured parse returned empty: {refusal or 'unknown'}"
    return parsed, ""
