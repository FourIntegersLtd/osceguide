"""Reading SCIM 2.0 requests (RFC 7643/7644) into roster terms. Pure: no I/O.

Only as much of SCIM as an identity provider's provisioning connector uses:
one-clause `eq` filters, and PATCH operations on the few attributes the roster
keeps. Attributes the roster does not store (a title, a department) are
ignored rather than refused, because Entra and Okta send them unasked and a
refusal would stop provisioning for everyone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"

# A connector asking for more than this in one page gets this many.
MAX_PAGE = 200

_FILTER = re.compile(r'^\s*([A-Za-z][\w.]*)\s+eq\s+"((?:[^"\\]|\\.)*)"\s*$', re.IGNORECASE)
_MEMBER_PATH = re.compile(r'^members\[\s*value\s+eq\s+"([^"]+)"\s*\]$', re.IGNORECASE)

USER_FILTERS = {"username": "userName", "emails": "emails", "emails.value": "emails", "id": "id"}
GROUP_FILTERS = {"displayname": "displayName", "id": "id"}


class InvalidFilter(ValueError):
    """Raised for a filter outside the one-clause `eq` form, or on an attribute we cannot match on."""


class InvalidPatch(ValueError):
    """Raised for a PATCH operation that is malformed, as opposed to merely about an attribute we ignore."""


def parse_filter(raw: str | None, *, allowed: dict[str, str]) -> tuple[str, str] | None:
    """`userName eq "a@b.com"` as `("userName", "a@b.com")`, or None for no filter.

    Attribute names are case-insensitive in SCIM; the canonical spelling is returned.
    """
    if raw is None or not raw.strip():
        return None
    matched = _FILTER.match(raw)
    if matched is None:
        raise InvalidFilter(raw)
    attribute = allowed.get(matched.group(1).lower())
    if attribute is None:
        raise InvalidFilter(raw)
    return attribute, matched.group(2).replace('\\"', '"')


def page_window(start_index: int | None, count: int | None) -> tuple[int, int]:
    """SCIM's 1-based `startIndex` and `count` as an offset and a limit, clamped."""
    offset = max((start_index or 1) - 1, 0)
    limit = MAX_PAGE if count is None else min(max(count, 0), MAX_PAGE)
    return offset, limit


def _as_bool(value: Any) -> bool:
    """A SCIM boolean. Entra sends `"False"` as a string in PATCH, so strings count."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise InvalidPatch(f"{value!r} is not a boolean")


@dataclass
class UserChanges:
    """What a PATCH asks of a user, in roster terms. None means untouched."""

    active: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    clear_first_name: bool = False
    clear_last_name: bool = False
    user_name: str | None = None


def user_patch(operations: list[dict[str, Any]]) -> UserChanges:
    """Fold a PATCH request's operations on a user into one set of changes."""
    changes = UserChanges()
    for operation in operations:
        action, path, value = _operation(operation)
        if path is None:
            if not isinstance(value, dict):
                raise InvalidPatch("an operation with no path needs an object value")
            for key, item in _flatten(value).items():
                _apply_user(changes, action, key, item)
        else:
            _apply_user(changes, action, path, value)
    return changes


@dataclass
class GroupChanges:
    """What a PATCH asks of a group: a new name, and members added, removed or replaced."""

    display_name: str | None = None
    replace_members: list[str] | None = None
    add_members: list[str] = field(default_factory=list)
    remove_members: list[str] = field(default_factory=list)


def group_patch(operations: list[dict[str, Any]]) -> GroupChanges:
    """Fold a PATCH request's operations on a group into one set of changes."""
    changes = GroupChanges()
    for operation in operations:
        action, path, value = _operation(operation)
        lowered = (path or "").lower()
        member_filter = _MEMBER_PATH.match(path or "")
        if member_filter and action == "remove":
            changes.remove_members.append(member_filter.group(1))
        elif lowered == "members":
            member_ids = _member_ids(value)
            if action == "add":
                changes.add_members.extend(member_ids)
            elif action == "remove":
                changes.remove_members.extend(member_ids)
            else:
                changes.replace_members = member_ids
        elif lowered == "displayname" and action in {"add", "replace"}:
            changes.display_name = _text(value)
        elif path is None and isinstance(value, dict):
            if "displayName" in value:
                changes.display_name = _text(value["displayName"])
            if "members" in value:
                changes.replace_members = _member_ids(value["members"])
    return changes


def apply_members(current: list[str], changes: GroupChanges) -> list[str]:
    """The membership after a PATCH: replaced, then added to, then removed from; order kept."""
    members = list(changes.replace_members) if changes.replace_members is not None else list(current)
    for member_id in changes.add_members:
        if member_id not in members:
            members.append(member_id)
    removed = set(changes.remove_members)
    return [member_id for member_id in members if member_id not in removed]


def _operation(operation: dict[str, Any]) -> tuple[str, str | None, Any]:
    """One PatchOp operation as (its `op` lower-cased, path, value)."""
    action = str(operation.get("op", "")).strip().lower()
    if action not in {"add", "replace", "remove"}:
        raise InvalidPatch(f"unknown op {operation.get('op')!r}")
    path = operation.get("path")
    return action, (str(path).strip() if path else None), operation.get("value")


def _apply_user(changes: UserChanges, action: str, path: str, value: Any) -> None:
    """One attribute of a user PATCH. Attributes the roster does not keep are ignored."""
    key = path.lower()
    if key == "active":
        changes.active = _as_bool(value) if action != "remove" else changes.active
    elif key == "name.givenname":
        if action == "remove" or value in (None, ""):
            changes.clear_first_name = True
        else:
            changes.first_name = _text(value)
    elif key == "name.familyname":
        if action == "remove" or value in (None, ""):
            changes.clear_last_name = True
        else:
            changes.last_name = _text(value)
    elif key == "username" and action != "remove":
        changes.user_name = _text(value)


def _flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """`{"name": {"givenName": "A"}}` as `{"name.givenName": "A"}`; dotted keys pass through."""
    flat: dict[str, Any] = {}
    for key, item in value.items():
        name = f"{prefix}{key}"
        if isinstance(item, dict) and not name.startswith("urn:"):
            flat.update(_flatten(item, f"{name}."))
        else:
            flat[name] = item
    return flat


def _member_ids(value: Any) -> list[str]:
    """The `value` of each `{"value": id}` in a members list."""
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    member_ids = []
    for member in value:
        if not isinstance(member, dict) or not member.get("value"):
            raise InvalidPatch("each member needs a value")
        member_ids.append(str(member["value"]))
    return member_ids


def _text(value: Any) -> str:
    """A string attribute, or a malformed-PATCH refusal."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidPatch(f"{value!r} is not a string")
    return value.strip()
