"""What the load does against a real database.

The transforms are pure and tested on fixtures; this is the other half —
whether the rows they describe can actually be written, and whether writing
them twice is a no-op. That second property is the one that matters: this runs
once, against data nobody can regenerate, and a partial run followed by a
fixed transform and a second pass must not duplicate somebody's history.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AssessmentResult, Attempt, TranscriptMessage
from app.features.entitlements.models import Entitlement
from app.features.identity.models import User
from app.migration import loader
from app.migration.attempts import LEGACY_POLICY_VERSION, attempt_from_transcript
from app.migration.users import entitlements_for, merge_users
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def b2c_user(email: str, app_type: str, doc_id: str, **overrides: object) -> dict:
    return {
        "id": doc_id,
        "email": email,
        "app_type": app_type,
        "username": "Alice",
        "created_at": "2026-01-15T09:00:00Z",
        "has_paid": False,
        **overrides,
    }


def b2c_transcript(user_id: str, transcript_id: str, turns: int = 2) -> dict:
    return {
        "transcript_id": transcript_id,
        "user_id": user_id,
        "mock_id": "m-1",
        "station_id": "s-1",
        "created_at": "2026-02-01T10:00:00Z",
        "transcript_message": [
            {"role": "assistant" if i % 2 else "user", "message": f"turn {i}", "timestamp": None}
            for i in range(turns)
        ],
    }


async def count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------


async def test_one_person_across_products_becomes_one_row_with_both_entitlements(
    db_session: AsyncSession,
) -> None:
    records = [
        b2c_user("Alice@Example.com", "sca", "fs-1", has_paid=True, plan_end_date="2027-01-01T00:00:00Z"),
        b2c_user("alice@example.com", "plab", "fs-2", has_paid=True),
    ]
    grants = [g for r in records for g in entitlements_for(r)]
    # The exams the import will name have to exist first. They used to be
    # seeded; the operator now supplies them, which is what `--exams` is for.
    for code in ("sca", "plab"):
        await ensure_exam(db_session, code)

    report, ids, _ = await loader.load_users(db_session, merge_users(records), grants)

    assert report.has_no_problems, report.problems
    assert report.users_created == 1
    assert report.entitlements_created == 2
    assert ids == {"fs-1": ids["fs-1"], "fs-2": ids["fs-1"]}, "both documents are the same person"
    assert await count(db_session, User) == 1


B2C_HASH = "$2b$12$7CnGAcydRjyhsnb2a3zOiOaeu/UrblrKtwwPDytxqMiVUgCJhGkC2"


async def test_a_b2c_hash_comes_across_as_legacy_never_as_a_current_password(
    db_session: AsyncSession,
) -> None:
    await loader.load_users(
        db_session,
        merge_users([b2c_user("bob@example.com", "sca", "fs-9", hashed_password=B2C_HASH)]),
    )

    user = await db_session.scalar(select(User).where(User.email == "bob@example.com"))
    assert user is not None
    assert user.password_hash is None
    assert user.legacy_password_hash == B2C_HASH
    assert user.must_change_password is False


async def test_a_person_with_no_usable_hash_still_resets(db_session: AsyncSession) -> None:
    await loader.load_users(
        db_session, merge_users([b2c_user("bob@example.com", "sca", "fs-9", hashed_password="")])
    )

    user = await db_session.scalar(select(User).where(User.email == "bob@example.com"))
    assert user is not None
    assert (user.password_hash, user.legacy_password_hash, user.must_change_password) == (None, None, True)


async def test_a_second_run_does_not_hand_a_legacy_hash_back(db_session: AsyncSession) -> None:
    """Someone who has since signed in (argon2, legacy dropped) keeps that."""
    records = [b2c_user("bob@example.com", "sca", "fs-9", hashed_password=B2C_HASH)]
    await loader.load_users(db_session, merge_users(records))
    user = await db_session.scalar(select(User).where(User.email == "bob@example.com"))
    assert user is not None
    user.password_hash = "$argon2id$their-own"
    user.legacy_password_hash = None
    await db_session.flush()

    await loader.load_users(db_session, merge_users(records))
    await db_session.refresh(user)

    assert (user.password_hash, user.legacy_password_hash) == ("$argon2id$their-own", None)


async def test_the_backfill_fills_only_imported_accounts_with_no_credential(
    db_session: AsyncSession,
) -> None:
    from app.features.identity import repository as identity_repo

    first = [b2c_user("old@example.com", "sca", "fs-1", hashed_password=B2C_HASH)]
    await loader.load_users(db_session, merge_users([b2c_user("old@example.com", "sca", "fs-1")]))
    # Not imported (no identity link), and one that already signs in with argon2.
    await identity_repo.create_user(db_session, email="invited@example.com", name="I", password_hash=None)
    signed_up = await identity_repo.create_user(
        db_session, email="signed@example.com", name="S", password_hash="$argon2id$x"
    )
    await loader.load_users(db_session, merge_users([b2c_user("signed@example.com", "sca", "fs-2")]))
    everyone = merge_users(
        [
            *first,
            b2c_user("invited@example.com", "sca", "fs-3", hashed_password=B2C_HASH),
            b2c_user("signed@example.com", "sca", "fs-2", hashed_password=B2C_HASH),
        ]
    )

    once = await loader.backfill_legacy_passwords(db_session, everyone)
    again = await loader.backfill_legacy_passwords(db_session, everyone)

    assert (once.legacy_passwords_backfilled, again.legacy_passwords_backfilled) == (1, 0)
    rows = {
        u.email: (u.password_hash, u.legacy_password_hash, u.must_change_password)
        for u in (await db_session.scalars(select(User))).all()
    }
    assert rows["old@example.com"] == (None, B2C_HASH, True)  # cleared by the legacy sign-in itself
    assert rows["invited@example.com"] == (None, None, False)
    assert rows["signed@example.com"] == ("$argon2id$x", None, False)
    assert signed_up.email == "signed@example.com"


async def test_the_backfill_leaves_alone_accounts_the_platform_left_without_a_password(
    db_session: AsyncSession,
) -> None:
    """The import links every account whose email is in the export, old ones included, so the link
    is not proof the import made the row. Each of these has no credential on purpose."""
    from app.features.identity import repository as identity_repo

    emails = ["filled@example.com", "sso@example.com", "taken@example.com", "invited@example.com"]
    emails += ["closed@example.com", "suspended@example.com"]
    users = {}
    for email in emails:
        users[email] = await identity_repo.create_user(
            db_session,
            email=email,
            name="P",
            password_hash="$argon2id$x" if email == "taken@example.com" else None,
        )
    await loader.load_users(
        db_session, merge_users([b2c_user(e, "sca", f"fs-{i}") for i, e in enumerate(emails)])
    )
    # An account the import itself would have made, linked and never touched since.
    # SSO created it, and SSO later proved the address on an account that had a password.
    for email in ("sso@example.com", "taken@example.com"):
        await identity_repo.link_identity(
            db_session, user_id=users[email].id, provider="oidc", subject=f"s-{email}", tenant_slug=None
        )
    await identity_repo.clear_password(db_session, users["taken@example.com"].id)
    await identity_repo.create_reset_token(
        db_session,
        user_id=users["invited@example.com"].id,
        token_hash="h" * 64,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    users["closed@example.com"].closed_at = datetime(2026, 1, 1, tzinfo=UTC)
    users["suspended@example.com"].status = "suspended"
    await db_session.flush()
    everyone = merge_users(
        [b2c_user(e, "sca", f"fs-{i}", hashed_password=B2C_HASH) for i, e in enumerate(emails)]
    )

    once = await loader.backfill_legacy_passwords(db_session, everyone)
    again = await loader.backfill_legacy_passwords(db_session, everyone)

    assert (once.legacy_passwords_backfilled, again.legacy_passwords_backfilled) == (1, 0)
    rows = {
        u.email: (u.password_hash, u.legacy_password_hash, u.must_change_password)
        for u in (await db_session.scalars(select(User))).all()
    }
    assert rows["filled@example.com"] == (None, B2C_HASH, False)
    for email in emails[1:]:
        assert rows[email][1] is None, email
    assert rows["invited@example.com"][2] is False


async def test_an_expired_grant_still_comes_across(db_session: AsyncSession) -> None:
    """ "Your access ended in March" is a better answer than an empty list."""
    await ensure_exam(db_session, "sca")
    record = b2c_user("carol@example.com", "sca", "fs-3", has_paid=True, plan_end_date="2025-03-01T00:00:00Z")
    await loader.load_users(db_session, merge_users([record]), entitlements_for(record))

    grant = await db_session.scalar(select(Entitlement))
    assert grant is not None
    assert grant.ends_at is not None and grant.ends_at.year == 2025
    assert grant.revoked_at is None


async def test_loading_people_twice_creates_nothing_the_second_time(
    db_session: AsyncSession,
) -> None:
    await ensure_exam(db_session, "sca")
    records = [b2c_user("dan@example.com", "sca", "fs-4", has_paid=True)]
    grants = entitlements_for(records[0])

    first, _, _ = await loader.load_users(db_session, merge_users(records), grants)
    second, _, _ = await loader.load_users(db_session, merge_users(records), grants)

    assert (first.users_created, first.entitlements_created) == (1, 1)
    assert (second.users_created, second.entitlements_created) == (0, 0)
    assert (second.users_matched, second.entitlements_existing) == (1, 1)
    assert await count(db_session, User) == 1
    assert await count(db_session, Entitlement) == 1


async def test_somebody_who_signed_up_before_their_import_keeps_their_password(
    db_session: AsyncSession,
) -> None:
    db_session.add(User(email="eve@example.com", name="Eve", password_hash="argon2-real"))
    await db_session.flush()

    report, _, _ = await loader.load_users(
        db_session, merge_users([b2c_user("EVE@example.com", "sca", "fs-5")])
    )

    assert report.users_matched == 1
    user = await db_session.scalar(select(User).where(User.email == "eve@example.com"))
    assert user is not None and user.password_hash == "argon2-real"


async def test_one_legacy_id_pointing_at_two_people_is_reported_not_guessed(
    db_session: AsyncSession,
) -> None:
    merged = merge_users(
        [b2c_user("f@example.com", "sca", "shared"), b2c_user("g@example.com", "plab", "shared")]
    )

    report, ids, _ = await loader.load_users(db_session, merged)

    assert not report.has_no_problems
    assert "shared" in report.problems[0]
    assert len(ids) == 1, "the ambiguous id resolves to one person, and the other is flagged"


# --------------------------------------------------------------------------
# Attempts
# --------------------------------------------------------------------------


async def _alice(session: AsyncSession) -> dict[str, object]:
    # The exam an imported attempt names has to exist before the import runs.
    # It used to be seeded; the operator supplies it now, which is what the
    # importer's `--exams` file is for.
    await ensure_exam(session, "sca")
    records = [b2c_user("alice@example.com", "sca", "fs-1")]
    _, ids, _ = await loader.load_users(session, merge_users(records))
    return ids  # type: ignore[return-value]


async def test_a_transcript_with_feedback_becomes_an_evaluated_attempt(
    db_session: AsyncSession,
) -> None:
    ids = await _alice(db_session)
    migrated = attempt_from_transcript(
        b2c_transcript("fs-1", "t-1"), app_type="sca", feedback={"overall": "good"}
    )

    report = await loader.load_attempts(db_session, [migrated], user_ids=ids)  # type: ignore[arg-type]

    assert report.has_no_problems, report.problems
    assert (report.attempts_created, report.messages_created, report.results_created) == (1, 2, 1)

    attempt = await db_session.scalar(select(Attempt))
    assert attempt is not None
    assert attempt.status == "evaluated"
    assert attempt.legacy_ref == "b2c:transcript_id:t-1"
    # Nothing reconstructs a definition: b2c never stored the rendered prompt
    # anywhere the export can reach, and inventing one would let a guess be
    # mistaken for what the candidate actually heard.
    assert attempt.definition is None


async def test_imported_feedback_is_tagged_so_it_is_never_charted_as_engine_output(
    db_session: AsyncSession,
) -> None:
    """Decision D-5: b2c's production scorer was never the engine."""
    ids = await _alice(db_session)
    migrated = attempt_from_transcript(
        b2c_transcript("fs-1", "t-2"), app_type="sca", feedback={"overall": "fine"}
    )
    await loader.load_attempts(db_session, [migrated], user_ids=ids)  # type: ignore[arg-type]

    result = await db_session.scalar(select(AssessmentResult))
    assert result is not None
    assert result.policy_version == LEGACY_POLICY_VERSION


async def test_an_empty_transcript_is_imported_as_failed_not_queued_for_scoring(
    db_session: AsyncSession,
) -> None:
    ids = await _alice(db_session)
    migrated = attempt_from_transcript(b2c_transcript("fs-1", "t-3", turns=0), app_type="sca")

    await loader.load_attempts(db_session, [migrated], user_ids=ids)  # type: ignore[arg-type]

    attempt = await db_session.scalar(select(Attempt))
    assert attempt is not None
    assert attempt.status == "failed"
    assert attempt.failed_reason == "empty_transcript"


async def test_loading_attempts_twice_duplicates_nothing(db_session: AsyncSession) -> None:
    """The property the whole design is for: a re-run is a no-op."""
    ids = await _alice(db_session)
    migrated = attempt_from_transcript(
        b2c_transcript("fs-1", "t-4", turns=3), app_type="sca", feedback={"overall": "ok"}
    )

    first = await loader.load_attempts(db_session, [migrated], user_ids=ids)  # type: ignore[arg-type]
    second = await loader.load_attempts(db_session, [migrated], user_ids=ids)  # type: ignore[arg-type]

    assert (first.attempts_created, first.messages_created, first.results_created) == (1, 3, 1)
    assert (second.attempts_created, second.messages_created, second.results_created) == (0, 0, 0)
    assert second.attempts_existing == 1
    assert await count(db_session, Attempt) == 1
    assert await count(db_session, TranscriptMessage) == 3
    assert await count(db_session, AssessmentResult) == 1


async def test_an_attempt_whose_author_is_not_in_the_export_is_reported_not_dropped(
    db_session: AsyncSession,
) -> None:
    ids = await _alice(db_session)
    migrated = attempt_from_transcript(b2c_transcript("fs-nobody", "t-5"), app_type="sca")

    report = await loader.load_attempts(db_session, [migrated], user_ids=ids)  # type: ignore[arg-type]

    assert not report.has_no_problems
    assert "fs-nobody" in report.problems[0]
    assert await count(db_session, Attempt) == 0


async def test_one_unusable_record_does_not_abandon_the_others(db_session: AsyncSession) -> None:
    ids = await _alice(db_session)
    good = attempt_from_transcript(b2c_transcript("fs-1", "t-6"), app_type="sca")
    orphan = attempt_from_transcript(b2c_transcript("fs-nobody", "t-7"), app_type="sca")

    report = await loader.load_attempts(db_session, [orphan, good], user_ids=ids)  # type: ignore[arg-type]

    assert len(report.problems) == 1
    assert report.attempts_created == 1
