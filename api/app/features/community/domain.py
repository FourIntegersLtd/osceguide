"""Rules for community posts.

Worth stating plainly: the legacy `community/*` routes carried no auth decorator at all, so anyone
who could reach the API could delete anyone's post.
"""

from __future__ import annotations

from collections.abc import Iterable

MAX_CONTENT = 10_000

# A handful of short lowercase keys, matching a fixed chip list of medical
# specialties. Validated here rather than trusted from the client.
MAX_TAGS = 5
MAX_TAG_LENGTH = 32


# What a question is filed under; its free-text tags are subtags of it.
CATEGORIES = ("general", "platform", "skills", "exam")
DEFAULT_CATEGORY = "general"
# The categories the assistant may answer: never the exam or skills ones, which need an expert.
ASSISTANT_CATEGORIES = ("general", "platform")
# The queue row `ask` writes for a question the assistant answers; `jobs.register` names the task.
ASSISTANT_QUEUE = "community"
ASSISTANT_TASK = "reply_as_assistant"


class InvalidCategory(Exception):
    """Raised when a category is not one of `CATEGORIES`."""

    pass


class ExamRequired(Exception):
    """Raised when an exam question names no exam."""

    pass


class NotYours(Exception):
    """Raised when someone tries to remove a post they may not moderate."""

    pass


class EmptyContent(Exception):
    """Raised when a post has nothing left in it once trimmed."""

    pass


class ContentTooLong(Exception):
    """Raised when a post's body is longer than `MAX_CONTENT` allows."""

    pass


class TagTooLong(Exception):
    """Raised when one of a question's tags is longer than `MAX_TAG_LENGTH`."""

    pass


class TooManyTags(Exception):
    """Raised when a question carries more tags than `MAX_TAGS` allows."""

    pass


def ensure_category(category: str, *, exam_code: str | None = None) -> str:
    """The category as stored. An exam question must say which exam."""
    ensure_known_category(category)
    if category == "exam" and not exam_code:
        raise ExamRequired("An exam question names its exam.")
    return category


def ensure_known_category(category: str) -> str:
    """The category, once it is known to be one of `CATEGORIES`."""
    if category not in CATEGORIES:
        raise InvalidCategory(f"A category is one of {', '.join(CATEGORIES)}.")
    return category


def clean(raw: str) -> str:
    """Trim the ends and leave the middle alone.

    Collapsing internal whitespace would quietly reformat someone's code block
    or list.
    """
    return (raw or "").strip()


def normalize_tag(raw: str) -> str:
    """One tag, the way it is stored and matched.

    Trimmed and lowercased, so a filter that matches "cardiology" also matches "Cardiology".
    """
    return (raw or "").strip().lower()


def clean_tags(raw: Iterable[str]) -> list[str]:
    """Normalize a question's tags: trim, lowercase, drop blanks, de-duplicate.

    Duplicates and blanks are normalized away rather than refused — the author
    meant one tag and the list should say so. Over-long and over-many are
    refusals, because guessing which tags to drop would silently post a
    question tagged differently from what its author asked.
    """
    tags: list[str] = []
    for raw_tag in raw:
        tag = normalize_tag(raw_tag)
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise TagTooLong(f"A tag is at most {MAX_TAG_LENGTH} characters.")
        if tag not in tags:
            tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise TooManyTags(f"A question carries at most {MAX_TAGS} tags.")
    return tags


def ensure_postable(raw: str) -> None:
    """Refuse a post that is empty once trimmed, or longer than `MAX_CONTENT`."""
    text = clean(raw)
    if not text:
        raise EmptyContent("There is nothing to post.")
    if len(text) > MAX_CONTENT:
        raise ContentTooLong(f"A post is at most {MAX_CONTENT} characters.")


def ensure_removable(
    *, author_id: str, actor_id: str, actor_is_admin: bool, actor_moderates_audience: bool = False
) -> None:
    """Your own, anyone's if you moderate the platform, or anyone's inside an institution you administer.

    Three separate permissions rather than one: an author deleting their own post, a platform
    moderator removing someone else's, and an institution keeping order in its own room.
    """
    if actor_is_admin or actor_moderates_audience or author_id == actor_id:
        return
    raise NotYours("You can only remove your own posts.")
