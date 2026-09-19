"""What the public forms will accept."""

from __future__ import annotations

import pytest

from app.features.public_site import domain


def test_a_contact_message_needs_an_address_to_reply_to() -> None:
    with pytest.raises(domain.InvalidMessage):
        domain.ensure_sendable(
            name="Amara", email="", body="How do I book?", kind=domain.MessageKind.CONTACT
        )
    with pytest.raises(domain.InvalidMessage):
        domain.ensure_sendable(
            name="Amara", email="not-an-address", body="How?", kind=domain.MessageKind.CONTACT
        )


def test_product_feedback_does_not_need_anybody_to_identify_themselves() -> None:
    """Somebody telling us a button is confusing should not have to sign it."""
    domain.ensure_sendable(
        name="", email="", body="The timer is hard to read.", kind=domain.MessageKind.PRODUCT_FEEDBACK
    )


def test_an_empty_message_is_nothing_to_send() -> None:
    for blank in ("", "   ", "\n\t "):
        with pytest.raises(domain.InvalidMessage):
            domain.ensure_sendable(
                name="A", email="a@b.com", body=blank, kind=domain.MessageKind.CONTACT
            )


def test_a_message_longer_than_the_column_is_refused_rather_than_truncated() -> None:
    with pytest.raises(domain.InvalidMessage):
        domain.ensure_sendable(
            name="A",
            email="a@b.com",
            body="x" * (domain.MAX_BODY + 1),
            kind=domain.MessageKind.CONTACT,
        )


def test_a_kind_no_form_sends_is_refused() -> None:
    assert domain.normalise_kind("CONTACT") is domain.MessageKind.CONTACT
    with pytest.raises(domain.InvalidMessage):
        domain.normalise_kind("complaint")
