"""Rostering rules, and resolving who is actually on a circuit.

b2b has no group-membership table: it matches a trainee's `cohort` field against
a group's `label`, both lowercased (`group_assignment.py:73-96`). Renaming a
group silently empties it and two groups sharing a label collide. Membership is
a table here; the label match survives only as a one-time importer.
"""

from __future__ import annotations

import pytest

from app.features.roster import domain
from app.migration import roster_labels


def test_an_email_identifies_a_trainee_within_an_organisation() -> None:
    assert domain.normalize_email("  Alice@Example.COM ") == "alice@example.com"


def test_a_group_label_is_normalised_for_comparison() -> None:
    """Oracle: the lowercase match b2b does at circuit-build time."""
    assert domain.normalize_label("  Cohort  A ") == "cohort a"


def test_two_spellings_of_a_label_are_the_same_group() -> None:
    assert domain.normalize_label("Cohort A") == domain.normalize_label("cohort a")


# --------------------------------------------------------------------------
# Resolving a circuit's roster
# --------------------------------------------------------------------------


def test_explicit_trainees_are_kept_in_order() -> None:
    resolved, warnings = domain.resolve_roster(explicit=["a", "b"], groups=[])
    assert resolved == ["a", "b"]
    assert warnings == []


def test_duplicates_are_removed_but_order_survives() -> None:
    resolved, _ = domain.resolve_roster(explicit=["a", "b", "a"], groups=[])
    assert resolved == ["a", "b"]


def test_group_members_are_appended_after_the_explicit_list() -> None:
    """Oracle: b2b appends resolved group members to the explicit ids."""
    resolved, _ = domain.resolve_roster(
        explicit=["a"], groups=[domain.GroupRef(group_id="g1", members=["b", "c"])]
    )
    assert resolved == ["a", "b", "c"]


def test_someone_in_both_the_list_and_a_group_appears_once() -> None:
    resolved, _ = domain.resolve_roster(
        explicit=["a"], groups=[domain.GroupRef(group_id="g1", members=["a", "b"])]
    )
    assert resolved == ["a", "b"]


def test_an_empty_group_is_reported_rather_than_ignored() -> None:
    """A supervisor who links a group and gets nobody should be told.

    b2b returns `assignmentWarnings` for this, and the warning is what stops an
    examination starting with half its candidates missing.
    """
    resolved, warnings = domain.resolve_roster(
        explicit=["a"], groups=[domain.GroupRef(group_id="g1", members=[])]
    )
    assert resolved == ["a"]
    assert warnings == [domain.RosterWarning(code="empty_group", group_id="g1")]


def test_several_groups_resolve_in_order() -> None:
    resolved, _ = domain.resolve_roster(
        explicit=[],
        groups=[
            domain.GroupRef(group_id="g1", members=["b"]),
            domain.GroupRef(group_id="g2", members=["a"]),
        ],
    )
    assert resolved == ["b", "a"]


# --------------------------------------------------------------------------
# Access
# --------------------------------------------------------------------------


def test_an_active_trainee_may_be_rostered() -> None:
    domain.ensure_rosterable(domain.TraineeState(access_revoked=False))


def test_a_revoked_trainee_may_not_be_rostered() -> None:
    """Otherwise revoking access still leaves them sitting next week's exam."""
    with pytest.raises(domain.TraineeRevoked):
        domain.ensure_rosterable(domain.TraineeState(access_revoked=True))


# --------------------------------------------------------------------------
# The importer that replaces label matching
# --------------------------------------------------------------------------


def test_the_importer_maps_cohort_labels_onto_group_membership() -> None:
    """One-time: turns b2b's implicit matching into rows, once, at migration.

    After that the table is the truth and renaming a group is just a rename.
    """
    pairs = roster_labels.memberships_from_labels(
        trainees=[("t1", "Cohort A"), ("t2", "cohort a"), ("t3", "Cohort B")],
        groups=[("g1", "Cohort A"), ("g2", "Cohort B")],
    )
    assert sorted(pairs) == [("g1", "t1"), ("g1", "t2"), ("g2", "t3")]


def test_the_importer_drops_trainees_whose_cohort_matches_nothing() -> None:
    pairs = roster_labels.memberships_from_labels(trainees=[("t1", "Nowhere")], groups=[("g1", "Cohort A")])
    assert pairs == []
