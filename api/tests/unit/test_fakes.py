"""The doubles conform to their ports and inject failure as documented."""

import pytest

from app.core.ports import Clock, EmailDeliveryFailed, EmailSender, SystemClock
from tests.support.fakes import FIXED_NOW, FakeClock, RecordingEmailSender


def test_clocks_conform_to_the_port() -> None:
    assert isinstance(FakeClock(), Clock)
    assert isinstance(SystemClock(), Clock)


def test_fake_clock_is_deterministic_and_advances() -> None:
    clock = FakeClock()
    assert clock.now() == FIXED_NOW
    clock.advance(90)
    assert (clock.now() - FIXED_NOW).total_seconds() == 90


async def test_email_sender_records_and_fails_on_cue() -> None:
    sender = RecordingEmailSender(fail_after=1)
    assert isinstance(sender, EmailSender)
    msg_id = await sender.send(to="a@b.com", subject="hi", html="<p>hi</p>")
    assert msg_id == "fake-msg-1"
    assert sender.sent[0].to == "a@b.com"
    with pytest.raises(EmailDeliveryFailed):
        await sender.send(to="c@d.com", subject="again", html="")
    assert len(sender.sent) == 1


def test_the_material_index_doubles_conform_to_the_port() -> None:
    """Both of them: the fake tests use, and the one an unconfigured deployment gets.

    `NoMaterialIndex` is production code, not a stub, so it belongs in the same
    assertion — a deployment without an embedding key runs it.
    """
    from app.core.ports import MaterialIndex
    from app.features.tutor_memory.index import NoMaterialIndex
    from tests.support.fakes import FakeMaterialIndex

    assert isinstance(FakeMaterialIndex(), MaterialIndex)
    assert isinstance(NoMaterialIndex(), MaterialIndex)


async def test_the_fake_material_index_filters_by_exam_like_the_real_one() -> None:
    """A fake that returned unentitled material would let an entitlement bug
    through every test above the adapter."""
    from tests.support.fakes import FakeMaterialIndex

    index = FakeMaterialIndex()
    await index.upsert(
        corpus="summary",
        source_id="locked",
        exam_id="exam-b",
        title="Not theirs",
        chunks=[{"index": 0, "section": "management", "text": "asthma advice"}],
    )

    assert await index.search(query="asthma", exam_ids=["exam-a"], corpus=None, limit=3) == []
    assert await index.search(query="asthma", exam_ids=["exam-b"], corpus=None, limit=3) != []


def test_the_checkout_fake_conforms_to_the_port() -> None:
    """The port exists so "this plan is not for sale" can be proven without
    an internet connection or a Stripe account."""
    from app.core.ports import CheckoutSessions
    from tests.support.fakes import FakeCheckoutSessions

    assert isinstance(FakeCheckoutSessions(), CheckoutSessions)
