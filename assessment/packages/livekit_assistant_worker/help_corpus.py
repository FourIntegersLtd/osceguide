"""Ranking a question against the FAQ corpus a session was given.

The corpus arrives in the bootstrap; this module holds only the matching
machinery, so the same worker answers from whatever content its backend
serves.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "how", "do", "i", "is", "are", "my", "me",
    "can", "where", "what", "when", "this", "that", "it", "be", "there", "here", "get", "find",
    "who", "why", "which",
})

EMPTY_QUERY_MESSAGE = "No search query provided. Ask the user to repeat their question."
NO_MATCH_PREFIX = "No matching FAQs found for this question."


class FaqEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    section: str = ""
    question: str
    answer: str


class HelpCorpus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    entries: tuple[FaqEntry, ...] = ()
    no_match_message: str = Field(default="Tell the user you cannot answer from the FAQ list.")
    # Names the backend knows are boilerplate in questions (its product, its persona):
    # the model tends to append them to queries, and they must not outrank the subject.
    boilerplate: tuple[str, ...] = ()

    def boilerplate_tokens(self) -> frozenset[str]:
        return frozenset(t for phrase in self.boilerplate for t in _tokenize(phrase))


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in text.lower().split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) >= 2 and token not in _STOPWORDS:
            tokens.add(token)
    return tokens


def score(query: str, entry: FaqEntry, *, ignore: frozenset[str] = frozenset()) -> float:
    query_norm = query.strip().lower()
    if not query_norm:
        return 0.0
    question_norm, answer_norm, section_norm = entry.question.lower(), entry.answer.lower(), entry.section.lower()
    haystack = f"{question_norm} {answer_norm} {section_norm}"

    total = 0.0
    if query_norm in question_norm:
        total += 12.0
    elif query_norm in haystack:
        total += 6.0

    query_tokens = _tokenize(query_norm)
    # Drop boilerplate only when something else is left: "what is <product>" must still match.
    query_tokens = (query_tokens - ignore) or query_tokens
    if not query_tokens:
        return total
    total += len(query_tokens & _tokenize(question_norm)) * 4.0
    total += len(query_tokens & _tokenize(answer_norm)) * 1.5
    total += len(query_tokens & _tokenize(section_norm)) * 1.0
    for token in query_tokens:
        if token in question_norm:
            total += 1.0
        elif token in answer_norm:
            total += 0.35
    return total


def search(corpus: HelpCorpus, query: str, *, limit: int = 5) -> tuple[str, int]:
    """Up to ``limit`` best entries formatted for the model, and how many matched."""
    cleaned = (query or "").strip()
    if not cleaned:
        return EMPTY_QUERY_MESSAGE, 0
    ignore = corpus.boilerplate_tokens()
    scored = ((score(cleaned, e, ignore=ignore), e) for e in corpus.entries)
    ranked = sorted((item for item in scored if item[0] > 0), key=lambda item: item[0], reverse=True)
    top = ranked[: max(1, limit)]
    if not top:
        return f"{NO_MATCH_PREFIX} {corpus.no_match_message}".strip(), 0
    lines = [f"Use ONLY the FAQ answers below. If none fit: {corpus.no_match_message}", ""]
    for _, entry in top:
        lines += [f"[{entry.section}]", f"QUESTION: {entry.question}", f"ANSWER: {entry.answer}", ""]
    return "\n".join(lines).strip(), len(top)
