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
