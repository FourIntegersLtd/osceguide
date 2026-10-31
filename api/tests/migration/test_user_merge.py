"""Merging one person out of five records.

A consumer exists as up to four Firestore documents — `users`, `plab_users`,
`casc_users`, `ortho_users` — and possibly a `b2b_users` row as well. Each
carries its own `has_paid` and `plan_end_date`. One person, one row here, and
the entitlements are the union.

These are pure functions with fixtures shaped like the real exports, so the
migration can be argued about before anybody runs it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.migration import users as transform

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def b2c(email: str, app_type: str, **overrides: object) -> dict:
    return {
        "email": email,
        "app_type": app_type,
        "username": "Someone",
        "created_at": "2026-01-15T09:00:00Z",
        "has_paid": False,
        **overrides,
    }


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------


def test_one_person_across_four_products_is_one_user() -> None:
    merged = transform.merge_users([b2c("Alice@Example.com", "sca"), b2c("alice@example.com", "plab")])
    assert len(merged) == 1
    assert merged[0].email == "alice@example.com"


def test_the_earliest_creation_date_wins() -> None:
    """Their account is as old as the first time they made one."""
    merged = transform.merge_users(
        [
            b2c("a@example.com", "sca", created_at="2026-03-01T00:00:00Z"),
            b2c("a@example.com", "plab", created_at="2026-01-01T00:00:00Z"),
        ]
    )
    assert merged[0].created_at.month == 1


def test_a_name_is_taken_from_whichever_record_has_one() -> None:
    merged = transform.merge_users(
        [b2c("a@example.com", "sca", username=""), b2c("a@example.com", "plab", username="Alice")]
    )
    assert merged[0].name == "Alice"


B2C_HASH = "$2b$12$7CnGAcydRjyhsnb2a3zOiOaeu/UrblrKtwwPDytxqMiVUgCJhGkC2"
OTHER_HASH = "$2b$12$" + "a" * 53


def test_a_b2c_bcrypt_hash_comes_across_as_a_legacy_credential() -> None:
    """The hash goes to `legacy_password_hash` only (never `password_hash`), and the person is
    not told to reset: they sign in with the password they have always used."""
    merged = transform.merge_users([b2c("a@example.com", "sca", hashed_password=B2C_HASH)])
    assert merged[0].legacy_password_hash == B2C_HASH
    assert merged[0].password_hash is None
    assert not merged[0].must_reset_password


def test_a_record_with_no_hash_carries_none_and_still_resets() -> None:
    for record in (b2c("a@example.com", "sca"), b2c("a@example.com", "sca", hashed_password="")):
        merged = transform.merge_users([record])
        assert merged[0].legacy_password_hash is None
        assert merged[0].must_reset_password


def test_an_sso_provisioned_record_carries_no_legacy_hash() -> None:
    """b2c stores a random unusable bcrypt hash for these; importing it would be a credential
    nobody can satisfy."""
    merged = transform.merge_users(
        [b2c("a@example.com", "sca", hashed_password=B2C_HASH, authProvider="clerk_sso")]
    )
    assert merged[0].legacy_password_hash is None
    assert merged[0].must_reset_password


def test_a_b2b_record_never_contributes_a_hash() -> None:
    """b2b's unsalted SHA-256 is deliberately never imported."""
    merged = transform.merge_users([], b2b_users=[{"email": "a@example.com", "hashed_password": "ab" * 32}])
    assert merged[0].legacy_password_hash is None
    assert merged[0].must_reset_password


def test_a_non_bcrypt_value_is_not_imported() -> None:
    merged = transform.merge_users([b2c("a@example.com", "sca", hashed_password="ab" * 32)])
    assert merged[0].legacy_password_hash is None


def test_an_sso_record_is_skipped_when_another_product_has_a_hash() -> None:
    merged = transform.merge_users(
        [
            b2c("a@example.com", "sca", hashed_password=OTHER_HASH, authProvider="clerk_sso"),
            b2c("a@example.com", "plab", hashed_password=B2C_HASH),
        ]
    )
    assert merged[0].legacy_password_hash == B2C_HASH


def test_products_that_agree_on_the_hash_need_no_choice() -> None:
    merged = transform.merge_users(
        [b2c("a@example.com", p, hashed_password=B2C_HASH) for p in ("sca", "plab")]
    )
    assert merged[0].legacy_password_hash == B2C_HASH


def test_differing_hashes_go_to_the_most_recently_used_product() -> None:
    merged = transform.merge_users(
        [
            b2c("a@example.com", "sca", hashed_password=OTHER_HASH, last_login="2026-01-01T00:00:00Z"),
            b2c("a@example.com", "plab", hashed_password=B2C_HASH, last_login="2026-06-01T00:00:00Z"),
        ]
    )
    assert merged[0].legacy_password_hash == B2C_HASH


def test_differing_hashes_that_cannot_be_ranked_carry_none_and_reset() -> None:
    """Guessing would let whoever registered an address on one product into the merged account."""
    merged = transform.merge_users(
        [
            b2c("a@example.com", "sca", hashed_password=OTHER_HASH),
            b2c("a@example.com", "plab", hashed_password=B2C_HASH),
        ]
    )
    assert merged[0].legacy_password_hash is None
    assert merged[0].must_reset_password


def test_platform_admin_comes_from_the_hardcoded_list() -> None:
    """b2c's admins are three literal email addresses. The migration is the last
    place that list exists."""
    merged = transform.merge_users(
        [b2c("hello@fourintegers.com", "sca")], admin_emails={"hello@fourintegers.com"}
    )
    assert merged[0].is_platform_admin


# --------------------------------------------------------------------------
# Entitlements
# --------------------------------------------------------------------------


def test_a_paid_product_becomes_an_entitlement() -> None:
    grants = transform.entitlements_for(
        b2c("a@example.com", "sca", has_paid=True, plan_end_date="2026-12-01T00:00:00Z")
    )
    assert [(g.exam_code, g.source) for g in grants] == [("sca", "purchase")]
    assert grants[0].ends_at is not None


def test_an_unpaid_product_grants_nothing() -> None:
    assert transform.entitlements_for(b2c("a@example.com", "sca", has_paid=False)) == []


def test_each_product_grants_its_own_exam() -> None:
    """The union, not the intersection: somebody who bought SCA and PLAB keeps
    both."""
    records = [
        b2c("a@example.com", "sca", has_paid=True, plan_end_date="2026-12-01T00:00:00Z"),
        b2c("a@example.com", "plab", has_paid=True, plan_end_date="2026-11-01T00:00:00Z"),
    ]
    grants = [g for record in records for g in transform.entitlements_for(record)]
    assert {g.exam_code for g in grants} == {"sca", "plab"}


def test_an_expired_plan_is_still_imported() -> None:
    """Expired, not dropped: "your access ended in March" is a better answer
    than an empty list, and the predicate already handles it."""
    grants = transform.entitlements_for(
        b2c("a@example.com", "sca", has_paid=True, plan_end_date="2020-01-01T00:00:00Z")
    )
    assert len(grants) == 1
    assert grants[0].ends_at is not None and grants[0].ends_at.year == 2020


def test_an_unknown_app_type_is_refused_rather_than_defaulted() -> None:
    """Defaulting to SCA is what the legacy code does; here it stops the import
    so somebody looks at it."""
    with pytest.raises(transform.UnknownLegacyProduct):
        transform.entitlements_for(b2c("a@example.com", "mrcp", has_paid=True))


# --------------------------------------------------------------------------
# Conflicts
# --------------------------------------------------------------------------


def test_a_b2b_row_merges_into_the_same_person() -> None:
    merged = transform.merge_users(
        [b2c("a@example.com", "sca")],
        b2b_users=[{"email": "A@Example.com", "name": "Alice B", "role": "admin"}],
    )
    assert len(merged) == 1
    assert merged[0].name in {"Someone", "Alice B"}


def test_a_b2b_only_person_still_becomes_a_user() -> None:
    merged = transform.merge_users([], b2b_users=[{"email": "only@b2b.com", "name": "Only"}])
    assert [u.email for u in merged] == ["only@b2b.com"]


def test_a_record_with_no_email_is_reported_not_imported() -> None:
    """Silently dropping somebody is worse than failing loudly."""
    with pytest.raises(transform.UnusableRecord):
        transform.merge_users([b2c("", "sca")])


# --------------------------------------------------------------------------
# Connecting attempts back to a person
# --------------------------------------------------------------------------


def test_every_legacy_document_id_is_kept_against_the_merged_user() -> None:
    """A transcript names its author by document id, never by email.

    Without these the loader cannot attach an imported attempt to anybody.
    """
    merged = transform.merge_users(
        [
            b2c("alice@example.com", "sca", id="fs-sca-1"),
            b2c("alice@example.com", "plab", id="fs-plab-7"),
        ],
        b2b_users=[{"email": "ALICE@example.com", "user_id": "b2b-99"}],
    )

    assert len(merged) == 1
    assert merged[0].legacy_ids == {"fs-sca-1", "fs-plab-7", "b2b-99"}


def test_a_record_without_a_document_id_still_merges() -> None:
    merged = transform.merge_users([b2c("bob@example.com", "sca")])
    assert merged[0].legacy_ids == set()
