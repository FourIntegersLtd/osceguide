"""The wording of an inbox message ."""

from __future__ import annotations

from app.features.inbox import domain


def test_report_answer_subject_names_the_station_when_known() -> None:
    assert domain.report_answer_subject("Chest pain") == "About your report: Chest pain"
    assert domain.report_answer_subject(None) == "About your station report"


def test_reply_subject_is_not_re_re() -> None:
    assert domain.reply_subject("Billing") == "Re: Billing"
    assert domain.reply_subject("Re: Billing") == "Re: Billing"
    assert domain.reply_subject(None) == "Re: your message to us"


def test_an_empty_answer_gets_a_default_body() -> None:
    assert domain.report_answer_body("  Fixed in v3.  ") == "Fixed in v3."
    assert domain.report_answer_body("  ") == domain.DEFAULT_ANSWER_BODY
    assert domain.report_answer_body(None) == domain.DEFAULT_ANSWER_BODY
