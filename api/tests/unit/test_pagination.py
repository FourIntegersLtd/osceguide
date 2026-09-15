import pytest

from app.core.errors import InvalidInput
from app.core.pagination import decode_cursor, encode_cursor


def test_cursor_round_trip() -> None:
    payload = {"created_at": "2026-09-15T10:00:00+00:00", "id": "abc"}
    assert decode_cursor(encode_cursor(payload)) == payload


def test_garbage_cursor_is_invalid_input() -> None:
    with pytest.raises(InvalidInput):
        decode_cursor("not-base64!!")
