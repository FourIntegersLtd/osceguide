"""TOTP sign-in: the gate, replay, recovery codes, and the challenge not being a session."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.core.settings import get_settings
from app.features.identity import repository
from app.features.identity.domain import MFA_VERIFY_TTL_SECONDS
from app.features.identity.service_sso import sign_in_external
from app.features.identity.tokens import MFA_CHALLENGE_TYPE, _hash_sync, issue_mfa_challenge
from app.features.tenancy import repository as tenancy_repository
from app.features.tenancy.models import AuditEntry
from tests.http.test_legacy_exchange_routes import CONSUMER_SECRET, legacy_token
from tests.http.test_results_routes import org_with_admin
from tests.support.tokens import bearer

# Two-factor sign-in is switched off for now (see finish_password_sign_in); unskip with it.
pytestmark = [pytest.mark.db, pytest.mark.skip(reason="two-factor sign-in switched off for now")]

PASSWORD = "correct horse battery"


class CountingRedis:
    """The rate limiter's Redis, counting in memory so the sixth attempt is visible."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def eval(self, script: str, numkeys: int, key: str, window: str) -> int:
        return await self.incr(key)

    async def ttl(self, key: str) -> int:
        return 60


async def _password_user(db_session: AsyncSession, *, email: str, platform_admin: bool = False) -> None:
    await repository.create_user(
        db_session,
        email=email,
        name="MFA Person",
        password_hash=_hash_sync(PASSWORD),
        is_platform_admin=platform_admin,
    )
    await db_session.flush()


def _code_at(secret: str, when: datetime) -> str:
    return pyotp.TOTP(secret).at(when)


async def _enrol(client: AsyncClient, email: str) -> tuple[str, str, list[str]]:
    """Sign in, enrol, and confirm. Returns the access token, the secret, and the recovery codes."""
    started = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "mfa_enrolment_required"
    challenge = started.json()["challenge_token"]
    secret_body = await client.post("/api/v1/auth/mfa/enrol/start", json={"challenge_token": challenge})
    assert secret_body.status_code == 200, secret_body.text
    secret = secret_body.json()["secret"]
    confirmed = await client.post(
        "/api/v1/auth/mfa/enrol/confirm",
        json={"challenge_token": challenge, "code": _code_at(secret, datetime.now(UTC))},
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "signed_in"
    assert len(body["recovery_codes"]) == 10
    return body["access_token"], secret, body["recovery_codes"]


async def test_sso_sign_in_does_not_ask_a_platform_admin_for_mfa(db_session: AsyncSession) -> None:
    email = f"sso-{uuid.uuid4()}@example.com"
    await repository.create_user(
        db_session,
        email=email,
        name="SSO Admin",
        password_hash=None,
        is_platform_admin=True,
    )
    await db_session.flush()

    async def memberships(session: AsyncSession, user_id: uuid.UUID) -> list[Membership]:
        del session, user_id
        return []

    result = await sign_in_external(
        db_session,
        provider="clerk",
        subject=f"subject-{email}",
        email=email,
        name="SSO Admin",
        tenant_slug=None,
        exam_code=None,
        settings=get_settings(),
        now=datetime.now(UTC),
        memberships_for=memberships,
    )
    assert result.status == "signed_in"
    assert result.access_token


async def test_a_challenge_token_is_refused_as_a_bearer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = f"bearer-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    started = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert started.status_code == 200
    assert started.json()["status"] == "mfa_enrolment_required"
    me = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {started.json()['challenge_token']}"}
    )
    assert me.status_code == 401


async def test_a_used_totp_step_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    email = f"replay-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    _token, secret, _codes = await _enrol(client, email)
    code = _code_at(secret, datetime.now(UTC) + timedelta(seconds=30))
    signed_in = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert signed_in.json()["status"] == "mfa_required"
    challenge = signed_in.json()["challenge_token"]
    first = await client.post("/api/v1/auth/mfa/verify", json={"challenge_token": challenge, "code": code})
    assert first.status_code == 200
    assert first.json()["status"] == "signed_in"
    again = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    replay = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": again.json()["challenge_token"], "code": code},
    )
    assert replay.status_code == 401
    assert replay.json()["code"] == "invalid_mfa_code"


async def test_a_recovery_code_works_once(client: AsyncClient, db_session: AsyncSession) -> None:
    email = f"recover-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    _token, _secret, codes = await _enrol(client, email)
    recovery = codes[0]
    first_login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    first = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": first_login.json()["challenge_token"], "recovery_code": recovery},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "signed_in"
    second_login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    second = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": second_login.json()["challenge_token"], "recovery_code": recovery},
    )
    assert second.status_code == 401
    assert second.json()["code"] == "invalid_mfa_code"


async def test_delete_is_refused_when_the_org_requires_staff_mfa(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = f"staff-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email)
    user = await repository.user_by_email(db_session, email)
    assert user is not None
    org = await tenancy_repository.create_organization(
        db_session, slug=f"mfa-{uuid.uuid4().hex[:8]}", name="MFA Org"
    )
    await tenancy_repository.update_organization(db_session, org.id, require_staff_mfa=True)
    await tenancy_repository.add_membership(db_session, org_id=org.id, user_id=user.id, role="supervisor")
    await db_session.flush()
    token, secret, _codes = await _enrol(client, email)
    code = _code_at(secret, datetime.now(UTC) + timedelta(seconds=30))
    refused = await client.request(
        "DELETE",
        "/api/v1/me/mfa",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": code},
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "mfa_required_by_policy"


async def test_the_sixth_verify_is_rate_limited(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = CountingRedis()
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: counter)
    email = f"limit-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    await _enrol(client, email)
    # Enrolment confirm shares this limit. The six verifies are what this test counts.
    counter.counts.clear()
    signed_in = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    challenge = signed_in.json()["challenge_token"]
    statuses = []
    for _attempt in range(6):
        response = await client.post(
            "/api/v1/auth/mfa/verify", json={"challenge_token": challenge, "code": "000000"}
        )
        statuses.append(response.status_code)
    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
    assert response.json()["code"] == "too_many_requests"


async def test_an_enrol_token_cannot_verify_and_a_challenge_cannot_enrol(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = f"kind-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    started = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert started.status_code == 200
    assert started.json()["status"] == "mfa_enrolment_required"
    _token, secret, _codes = await _enrol(client, email)
    signed_in = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert signed_in.json()["status"] == "mfa_required"
    enrol_token = started.json()["challenge_token"]
    wrong_verify = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": enrol_token, "code": _code_at(secret, datetime.now(UTC))},
    )
    assert wrong_verify.status_code == 401
    assert wrong_verify.json()["code"] == "mfa_challenge_expired"
    wrong_enrol = await client.post(
        "/api/v1/auth/mfa/enrol/start",
        json={"challenge_token": signed_in.json()["challenge_token"]},
    )
    assert wrong_enrol.status_code == 401
    assert wrong_enrol.json()["code"] == "mfa_challenge_expired"


async def test_an_expired_challenge_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    email = f"expired-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    user = await repository.user_by_email(db_session, email)
    assert user is not None
    user_id = user.id
    token = issue_mfa_challenge(
        user_id,
        token_type=MFA_CHALLENGE_TYPE,
        ttl_seconds=MFA_VERIFY_TTL_SECONDS,
        settings=get_settings(),
        now=datetime.now(UTC) - timedelta(minutes=10),
    )
    refused = await client.post("/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": "000000"})
    assert refused.status_code == 401
    assert refused.json()["code"] == "mfa_challenge_expired"


async def test_verify_is_refused_when_sso_only_disables_password_login(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = f"sso-only-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    _token, secret, _codes = await _enrol(client, email)
    signed_in = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert signed_in.json()["status"] == "mfa_required"
    user = await repository.user_by_email(db_session, email)
    assert user is not None
    await repository.disable_password_login(db_session, user.id)
    db_session.expire_all()
    refused = await client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": signed_in.json()["challenge_token"],
            "code": _code_at(secret, datetime.now(UTC) + timedelta(seconds=30)),
        },
    )
    assert refused.status_code == 401
    assert refused.json()["code"] == "password_login_disabled"


async def test_a_platform_admin_resets_mfa_and_others_are_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    email = f"reset-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    enrolled = await repository.user_by_email(db_session, email)
    assert enrolled is not None
    enrolled_id = enrolled.id
    bare_email = f"bare-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=bare_email)
    bare = await repository.user_by_email(db_session, bare_email)
    assert bare is not None
    bare_id = bare.id
    token, _secret, _codes = await _enrol(client, email)
    root = await make_actor(f"root-reset-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    outsider = await make_actor(f"outsider-{uuid.uuid4().hex[:8]}@example.com")

    reset = await client.post(f"/api/v1/platform/users/{enrolled_id}/reset-mfa", headers=bearer(root))
    assert reset.status_code == 204
    status_read = await client.get("/api/v1/me/mfa", headers={"Authorization": f"Bearer {token}"})
    assert status_read.status_code == 200
    assert status_read.json()["enabled"] is False
    entries = (
        (
            await db_session.execute(
                select(AuditEntry).where(
                    AuditEntry.action == "mfa.reset_by_admin",
                    AuditEntry.target_id == str(enrolled_id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert [entry.action for entry in entries] == ["mfa.reset_by_admin"]

    missing = await client.post(f"/api/v1/platform/users/{bare_id}/reset-mfa", headers=bearer(root))
    assert missing.status_code == 409
    assert missing.json()["code"] == "mfa_not_enrolled"
    refused = await client.post(f"/api/v1/platform/users/{enrolled_id}/reset-mfa", headers=bearer(outsider))
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"


async def test_mfa_policy_is_changed_by_an_institution_admin_and_audited(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    _other_org, other = await org_with_admin(client, make_actor, slug="guys")
    supervisor = await make_actor(
        f"sup-policy-{uuid.uuid4().hex[:8]}@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    root = await make_actor(f"root-policy-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)

    changed = await client.patch(
        "/api/v1/orgs/kings/mfa-policy",
        json={"require_staff_mfa": True},
        headers=bearer(admin),
    )
    assert changed.status_code == 200
    assert changed.json()["require_staff_mfa"] is True
    entries = (
        (
            await db_session.execute(
                select(AuditEntry).where(
                    AuditEntry.org_id == org_id, AuditEntry.action == "org.mfa_policy_changed"
                )
            )
        )
        .scalars()
        .all()
    )
    assert [entry.action for entry in entries] == ["org.mfa_policy_changed"]

    by_root = await client.patch(
        "/api/v1/orgs/kings/mfa-policy",
        json={"require_staff_mfa": False},
        headers=bearer(root),
    )
    assert by_root.status_code == 200

    refused_other = await client.patch(
        "/api/v1/orgs/kings/mfa-policy",
        json={"require_staff_mfa": True},
        headers=bearer(other),
    )
    assert refused_other.status_code == 403
    assert refused_other.json()["code"] == "forbidden"
    refused_supervisor = await client.patch(
        "/api/v1/orgs/kings/mfa-policy",
        json={"require_staff_mfa": True},
        headers=bearer(supervisor),
    )
    assert refused_supervisor.status_code == 403
    assert refused_supervisor.json()["code"] == "forbidden"


async def test_legacy_exchange_of_an_enrolled_user_requires_mfa(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = f"legacy-mfa-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    await _enrol(client, email)
    exchanged = await client.post(
        "/api/v1/auth/exchange-legacy",
        json={"provider": "consumer", "token": legacy_token(secret=CONSUMER_SECRET, email=email)},
    )
    assert exchanged.status_code == 200
    assert exchanged.json()["status"] == "mfa_required"


async def test_an_old_recovery_code_is_refused_after_regeneration(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    email = f"regen-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    token, secret, codes = await _enrol(client, email)
    old = codes[0]
    regenerated = await client.post(
        "/api/v1/me/mfa/recovery-codes",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": _code_at(secret, datetime.now(UTC) + timedelta(seconds=30))},
    )
    assert regenerated.status_code == 200, regenerated.text
    new_code = regenerated.json()["recovery_codes"][0]
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    worked = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": login.json()["challenge_token"], "recovery_code": new_code},
    )
    assert worked.status_code == 200
    assert worked.json()["status"] == "signed_in"
    again = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    refused = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": again.json()["challenge_token"], "recovery_code": old},
    )
    assert refused.status_code == 401
    assert refused.json()["code"] == "invalid_mfa_code"


async def test_the_sixth_recovery_regeneration_is_rate_limited(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = CountingRedis()
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: counter)
    email = f"regen-limit-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    token, _secret, _codes = await _enrol(client, email)
    counter.counts.clear()
    statuses = []
    response = None
    for _attempt in range(6):
        response = await client.post(
            "/api/v1/me/mfa/recovery-codes",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "000000"},
        )
        statuses.append(response.status_code)
    assert response is not None
    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
    assert response.json()["code"] == "too_many_requests"


async def test_a_password_alone_does_not_reopen_a_closed_account_with_an_authenticator(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Closing is undone only by a complete sign-in: the password earns a challenge and the
    account stays closed (erasure still due) until the code is verified."""
    email = f"closed-{uuid.uuid4()}@example.com"
    await _password_user(db_session, email=email, platform_admin=True)
    token, secret, _codes = await _enrol(client, email)
    closed = await client.post("/api/v1/me/close", json={"password": PASSWORD}, headers=bearer(token))
    assert closed.status_code == 204, closed.text

    started = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert started.json()["status"] == "mfa_required"
    user = await repository.user_by_email(db_session, email)
    assert user is not None
    await db_session.refresh(user)
    assert user.status == "deleted"

    verified = await client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "challenge_token": started.json()["challenge_token"],
            "code": _code_at(secret, datetime.now(UTC) + timedelta(seconds=30)),
        },
    )
    assert verified.json()["status"] == "signed_in"
    await db_session.refresh(user)
    assert (user.status, user.closed_at) == ("active", None)
