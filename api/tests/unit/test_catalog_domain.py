"""An exam is written, not shipped.

This file used to assert that exactly four exams existed, that their codes were
`sca`, `plab`, `casc` and `ortho`, that each bound a particular framework id,
and that the tuple declaring all that matched a seed in a migration — which it
loaded by literal path. Adding a fifth exam meant editing the tuple, the seed
and these tests together.

None of that is a rule about exams. What is left below is: a code has to be
usable in a URL, an exam nobody can sit cannot be built on, and an exam cannot
be published until it is clear what it is marked against.
"""

from __future__ import annotations

import uuid

import pytest

from app.features.catalog import domain

RUBRIC = uuid.uuid4()


@pytest.mark.parametrize("raw", ["sca", " SCA ", "Sca", "frcs-ortho", "gp_sca"])
def test_a_code_is_normalised_to_one_spelling(raw: str) -> None:
    """Case and space are not meaningful, so they are removed once, here."""
    assert domain.normalise_code(raw) == raw.strip().lower()


@pytest.mark.parametrize("raw", ["", "a", "9sca", "has space", "UPPER ONLY!", "x" * 40, "sca/plab"])
def test_a_code_that_could_not_live_in_a_url_is_refused(raw: str) -> None:
    """It appears in a plan's `exam_code`, in a partner ref id, and in paths."""
    with pytest.raises(domain.InvalidExamCode):
        domain.normalise_code(raw)


def test_any_code_is_allowed_that_could_be_one() -> None:
    """There is no list of permitted exams. That was the whole problem."""
    assert domain.normalise_code("mrcp-paces") == "mrcp-paces"
    assert domain.normalise_code("mrcog-part-3") == "mrcog-part-3"


# --- lifecycle --------------------------------------------------------------


def test_an_exam_cannot_be_published_without_a_rubric() -> None:
    """Otherwise it could be sat, and found unmarkable when the transcript arrived."""
    with pytest.raises(domain.NotPublishable, match="marked against"):
        domain.ensure_publishable(domain.ExamStatus.DRAFT, None)


def test_publishing_needs_only_a_rubric() -> None:
    assert domain.ensure_publishable(domain.ExamStatus.DRAFT, RUBRIC) is domain.ExamStatus.PUBLISHED


def test_a_retired_exam_is_not_brought_back() -> None:
    """A new exam is the honest way: its past attempts stay what they were."""
    with pytest.raises(domain.NotPublishable):
        domain.ensure_publishable(domain.ExamStatus.RETIRED, RUBRIC)


def test_only_a_published_exam_is_retired() -> None:
    assert domain.ensure_retirable(domain.ExamStatus.PUBLISHED) is domain.ExamStatus.RETIRED
    with pytest.raises(domain.NotRetirable):
        domain.ensure_retirable(domain.ExamStatus.DRAFT)


@pytest.mark.parametrize("status", [domain.ExamStatus.DRAFT, domain.ExamStatus.RETIRED])
def test_nothing_may_be_built_on_an_exam_nobody_can_sit(status: domain.ExamStatus) -> None:
    """Programmes, entitlements, stations and plans all go through this."""
    with pytest.raises(domain.NotOfferable):
        domain.ensure_offerable(status)


def test_a_published_exam_may_be_built_on() -> None:
    assert domain.ensure_offerable(domain.ExamStatus.PUBLISHED) is None


# --- programmes -------------------------------------------------------------


def test_only_an_active_programme_is_offered() -> None:
    assert domain.ProgrammeRef(exam_code="sca", status="active").is_offerable
    assert not domain.ProgrammeRef(exam_code="sca", status="draft").is_offerable
    assert not domain.ProgrammeRef(exam_code="sca", status="retired").is_offerable


def test_the_catalogue_no_longer_hard_codes_any_exam() -> None:
    """The regression this whole change exists to prevent."""
    assert not hasattr(domain, "PUBLISHED_EXAMS")
    assert not hasattr(domain, "exam_by_code")


# --- ownership ---------------------------------------------------------------


def test_the_platform_has_no_org_and_an_institution_does() -> None:
    assert domain.owner_of(None) is domain.OwnerKind.PLATFORM
    assert domain.owner_of(uuid.uuid4()) is domain.OwnerKind.ORG


def test_only_an_exams_own_owner_may_change_it() -> None:
    """Writing is narrower than reading. An institution reads our catalogue as
    well as its own, but neither side may edit the other's exam — which is what
    keeps the two lifecycles from dragging each other."""
    ashford = uuid.uuid4()
    kings = uuid.uuid4()

    domain.ensure_owned_by(None, None)  # the platform, at its own exam
    domain.ensure_owned_by(ashford, ashford)  # a school, at its own

    with pytest.raises(domain.NotOwned):
        domain.ensure_owned_by(None, ashford)  # a school at ours
    with pytest.raises(domain.NotOwned):
        domain.ensure_owned_by(ashford, None)  # us at a school's
    with pytest.raises(domain.NotOwned):
        domain.ensure_owned_by(ashford, kings)  # one school at another's
