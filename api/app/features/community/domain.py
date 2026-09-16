"""Rules for community posts.

Worth stating plainly because the legacy routes have none: in b2c,
`add_comment`, `delete_comment` and every `community/*` route carries no auth
decorator at all, so anyone who can reach the API can delete anyone's post.
"""

from __future__ import annotations

MAX_CONTENT = 10_000


class NotYours(Exception):
    pass


class EmptyContent(Exception):
    pass


class ContentTooLong(Exception):
    pass


def clean(raw: str) -> str:
    """Trim the ends and leave the middle alone.

    Collapsing internal whitespace would quietly reformat someone's code block
    or list.
    """
    return (raw or "").strip()


def ensure_postable(raw: str) -> None:
    text = clean(raw)
    if not text:
        raise EmptyContent("There is nothing to post.")
    if len(text) > MAX_CONTENT:
        raise ContentTooLong(f"A post is at most {MAX_CONTENT} characters.")


def ensure_removable(*, author_id: str, actor_id: str, actor_is_admin: bool) -> None:
    """Your own, or anyone's if you moderate.

    Two separate permissions rather than one: an author deleting their own post
    and a moderator removing someone else's are different acts, and conflating
    them is how the legacy routes ended up with neither.
    """
    if actor_is_admin or author_id == actor_id:
        return
    raise NotYours("You can only remove your own posts.")


def apply_like(*, already_liked: bool) -> bool:
    """A like is a fact about a person, not a counter.

    b2c increments a number, so a double tap counts twice and there is no way to
    undo one. Storing who liked what makes both questions answerable.
    """
    return True


def apply_unlike(*, already_liked: bool) -> bool:
    return False
