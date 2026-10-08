"""Delivering queued mail, and when to stop trying."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.features.notifications import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def test_backoff_grows_with_each_attempt() -> None:
    """A provider that is down stays down for a while; retrying every second
    makes that worse for everyone."""
    delays = [domain.retry_delay(attempt) for attempt in range(1, 5)]
    assert delays == sorted(delays)
    assert delays[0] < delays[-1]


def test_backoff_is_capped() -> None:
    assert domain.retry_delay(99) == domain.MAX_RETRY_SECONDS


def test_a_message_is_abandoned_after_enough_attempts() -> None:
    """Abandoned, not retried forever: somebody has to look at it."""
    assert not domain.should_retry(attempts=domain.MAX_ATTEMPTS)
    assert domain.should_retry(attempts=domain.MAX_ATTEMPTS - 1)


def test_the_next_attempt_is_scheduled_from_now() -> None:
    assert domain.next_available(attempts=1, now=NOW) == NOW + timedelta(seconds=domain.retry_delay(1))


def test_the_invitation_email_carries_the_link_and_the_board_wording() -> None:
    from app.features.notifications import service

    html = service._render("invitation", {"token": "tok123", "invited_to": "Kings <b>"})
    assert "/accept-invitation?token=tok123" in html
    assert "Kings &lt;b&gt; has invited you to OSCE Guide. Set a password to get started." in html
    assert ">Set your password</a>" in html
    assert "This link expires in 7 days." in html


def test_the_receipt_email_links_to_the_receipts_in_settings() -> None:
    from app.features.notifications import service

    html = service._render(
        "payment_receipt",
        {
            "amount_total": "£22.49",
            "receipt_id": "R-1",
            "plan_label": "SCA 1 month",
            "plan_end_date": "1 Nov 2026",
        },
    )
    assert '/app/me/settings" style=' in html
    assert ">Open your receipts</a>" in html


def test_the_session_reminder_links_to_the_session_and_reads_the_time_in_words() -> None:
    from app.features.notifications import service

    html = service._render(
        "marketplace_session_reminder",
        {
            "username": "Ann",
            "partner_username": "Bo",
            "scheduled_at": "2026-10-09T14:30:00+00:00",
            "peer_session_id": "abc-123",
        },
    )
    assert '/app/me/marketplace/session/abc-123">Open the session</a>' in html
    assert "at Friday 9 October 2026, 14:30 UTC." in html
    assert "2026-10-09T" not in html


def test_an_unknown_template_key_is_an_error_not_an_email() -> None:
    import pytest

    from app.features.notifications import service

    with pytest.raises(service.UnknownTemplate):
        service._render("no_such_template", {"a": "b"})


def test_the_practice_access_email_opens_the_practice_area_not_the_sign_in_page() -> None:
    """E-5: the link used to be /login, a dead end for someone already signed in."""
    from app.features.notifications import service

    html = service._render("practice_access_granted", {"exam_title": "SCA", "granted_by": "Kings"})
    assert '/app/me" style=' in html
    assert "/login" not in html
    assert ">Start practising</a>" in html


def test_the_expiry_warning_names_the_exam_and_the_end_date() -> None:
    from app.features.notifications import service

    html = service._render("entitlement_expiring", {"exam_title": "SCA <b>", "ends_on": "15 October 2026"})
    assert "Your SCA &lt;b&gt; access ends on 15 October 2026</h1>" in html
    assert '/app/me/settings" style=' in html


def test_the_institution_emails_link_to_the_sitting_and_the_circuit() -> None:
    from app.features.notifications import service

    fields = {
        "org_slug": "kings",
        "org_name": "Kings",
        "sitting_id": "s1",
        "sitting_name": "Finals",
        "circuit_id": "c1",
        "circuit_name": "Room 1",
        "scheduled_at": "2026-11-03T10:00:00+00:00",
    }
    for key in ("sitting_scheduled", "exam_day_reminder"):
        assert "/app/kings/trainee/sittings/s1" in service._render(key, fields)
    assert "/app/kings/circuits/c1" in service._render("review_assigned", fields)
