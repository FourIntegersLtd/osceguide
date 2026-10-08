"""What tenancy's routes read and return: organisations, memberships, the
platform console's accounts and its audit log.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

# Re-exported so tenancy's own resend route shares this shape with roster's
# rather than FastAPI qualifying two identically named classes in openapi.json.
from app.core.schemas import InvitationRead as InvitationRead


class OrganizationRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    org_type: str
    status: str
    created_at: datetime
    contract_starts_at: datetime | None = None
    contract_ends_at: datetime | None = None
    require_staff_mfa: bool = False
    contact_name: str | None = None
    contact_email: str | None = None
    # The organisation this one sits under (a trust above its hospitals), or
    # null for a top-level organisation.
    parent_org_id: uuid.UUID | None = None


class UpdateOrganization(BaseModel):
    """What a platform administrator may change about an organisation. Not the slug."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    org_type: str | None = Field(default=None, max_length=32)
    contract_starts_at: datetime | None = None
    contract_ends_at: datetime | None = None
    require_staff_mfa: bool | None = None
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None


class UpdateOrgDetails(BaseModel):
    """What an org admin may change: the name and contact. Not the address or contract.

    A contact sent as null is cleared; one left out is kept.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None


class StaffMfaPolicy(BaseModel):
    """Whether this organisation's staff must sign in with a second factor."""

    require_staff_mfa: bool


class UserSummary(BaseModel):
    """An account as the console lists it. No password state, no memberships."""

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    is_platform_admin: bool = False
    # `active` or `deactivated`. Was missing from the detail too, so the
    # console's Deactivate button could never say which state it was in.
    status: str = "active"


class UpdatePlatformUser(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    exam_code: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(default=None, pattern="^(active|deactivated)$")
    exam_date: date | None = None
    # An access arrangement, gating the two custom timers below — replaces the
    # old bare "yes" `extra_reading_percent` on this surface (A3).
    needs_extra_time: bool | None = None
    custom_reading_seconds: int | None = Field(default=None, ge=1, le=3659)
    custom_simulation_seconds: int | None = Field(default=None, ge=1, le=3659)


class PlatformUserDetail(UserSummary):
    """Support view: memberships and account flags the list row omits."""

    must_change_password: bool = False
    last_login_at: datetime | None = None
    exam_code: str | None = None
    exam_date: date | None = None
    needs_extra_time: bool = False
    custom_reading_seconds: int | None = None
    custom_simulation_seconds: int | None = None
    consumer_role: str = "user"
    legacy_consumer_ids: dict[str, str] = Field(default_factory=dict)
    memberships: list[MembershipRead] = Field(default_factory=list)


class SetPlatformAdmin(BaseModel):
    """Grant or revoke, spelled out rather than implied by which route was called."""

    is_platform_admin: bool


class InvitePlatformAdmin(BaseModel):
    email: EmailStr
    # Blank keeps the old behaviour of naming a new account after its address.
    name: str | None = Field(default=None, max_length=200)


class PlatformAdminInviteRead(BaseModel):
    user: UserSummary
    # True when the account was created and emailed a link to choose a password.
    invited: bool = False


class OrgAtRisk(BaseModel):
    """An organisation the console should look at before it looks at anything else."""

    slug: str
    name: str
    status: str
    contract_ends_at: datetime | None
    # `suspended`, `contract_lapsed` (ended, not yet swept) or `contract_ending`
    # (within thirty days).
    reason: str


class PlatformOverview(BaseModel):
    organizations: int
    users: int
    organizations_by_status: dict[str, int] = Field(default_factory=dict)
    at_risk: list[OrgAtRisk] = Field(default_factory=list)


class RenewContract(BaseModel):
    """New contract dates, and whether a suspension should lift with them."""

    contract_starts_at: datetime | None = None
    contract_ends_at: datetime
    restore: bool = True


class CreateOrganization(BaseModel):
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-]*$")
    name: str = Field(min_length=1, max_length=200)
    org_type: str = Field(default="institution", pattern="^(institution|partner|employer)$")


class MembershipRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str | None = None
    role: str
    product_surface: str | None = None
    status: str
    revoked_at: datetime | None = None
    # True when adding this membership created the account and queued an
    # invitation: the person cannot sign in until they choose a password.
    invited: bool = False
    # True when this call created the account and gave it the temporary password the
    # admin typed; false when the account already existed and the password was ignored.
    temporary_password_applied: bool = False
    # Circuits this person is named supervisor of; filled by the list read.
    circuits_led: int = 0
    # Which organisation, for a list that spans several (a person's detail page).
    org_slug: str | None = None
    org_name: str | None = None
    # True while the password the account holds is one an admin chose and the person has not replaced.
    must_change_password: bool = False


class CreateMembership(BaseModel):
    email: EmailStr
    role: str = Field(min_length=1, max_length=32)
    product_surface: str | None = None


class SeatMembership(CreateMembership):
    """An add by an admin that may hand a new account a temporary password (the platform
    console's seat route and an organisation's team invite).

    Only for an address with no account yet, and only because the invitation email
    cannot always be delivered. The person must change it at first sign-in. Ignored for
    an address that already has an account: the console never resets anyone's password.
    """

    temporary_password: str | None = Field(default=None, min_length=1, max_length=512)


class ReissueTemporaryPassword(BaseModel):
    temporary_password: str = Field(min_length=1, max_length=512)


class UpdateMembership(BaseModel):
    role: str = Field(min_length=1, max_length=32)


MAX_BULK_MEMBERSHIPS = 500


class BulkCreateMemberships(BaseModel):
    """A team at once, in one request. Capped so one request cannot invite a whole
    hospital by accident."""

    memberships: list[CreateMembership] = Field(min_length=1, max_length=MAX_BULK_MEMBERSHIPS)


class SkippedMembership(BaseModel):
    email: str
    role: str
    # A stable code the client switches on: `membership_exists` for a person
    # already holding this role, in this upload or already on the team.
    code: str


class BulkMembershipsResult(BaseModel):
    """Who joined and who was already there, so a partial upload is not a mystery."""

    created: list[MembershipRead] = Field(default_factory=list)
    skipped: list[SkippedMembership] = Field(default_factory=list)


class BulkMembershipIds(BaseModel):
    """A batch of membership ids, for a bulk action from a selection in the
    team table. Capped the same as a bulk import, so a selected page cannot
    name a whole organisation's team by accident.
    """

    membership_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_BULK_MEMBERSHIPS)


class BulkMembershipRevokeResult(BaseModel):
    """One row's outcome from a bulk revoke: whether this call changed
    anything, or the row was already in that state or not this
    organisation's to change.
    """

    membership_id: uuid.UUID
    outcome: str  # "revoked" | "already_revoked" | "not_found"


class BulkMembershipRevokeResponse(BaseModel):
    results: list[BulkMembershipRevokeResult]


class BulkMembershipInvitationResult(BaseModel):
    membership_id: uuid.UUID
    outcome: str  # "sent" | "already_accepted" | "not_found"


class BulkMembershipInvitationResponse(BaseModel):
    results: list[BulkMembershipInvitationResult]


class SwitchWorkspace(BaseModel):
    """Which workspace to re-issue the token against. `None` means the person's own practice
    — a real destination, not an absence."""

    org_slug: str | None = None


class WorkspaceToken(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int
    active_org_slug: str | None
    active_role: str | None


class AuditRead(BaseModel):
    id: uuid.UUID
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    summary: str | None
    at: datetime


class PlatformAuditRead(AuditRead):
    """An audit row as the console reads it across every organisation. `org_id` is None for
    the platform's own acts."""

    org_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    meta: dict[str, Any] | None = None


class Capabilities(BaseModel):
    """What the caller may do, decided here rather than duplicated in the frontend."""

    user_id: uuid.UUID
    is_platform_admin: bool
    active_org_slug: str | None
    active_role: str | None
    can: dict[str, bool]
