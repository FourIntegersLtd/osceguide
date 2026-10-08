/**
 * The team: an organisation's staff.
 *
 * Who may run a circuit and who may sign off a result. Deliberately its own
 * slice, separate from `roster/api.ts`: the retiring client ran staff and
 * examined trainees through one seven-hundred-line `useOrgTeamPage` hook, which
 * is how "Remove from team" came to mean either a staff login or a candidate
 * depending on which tab happened to be open.
 */
import { platformRequest, type components } from "@/foundation/platform-client";
import type { WithTemporaryPassword } from "@/foundation/ui/useTemporaryPassword";
import { orgPath, pageQuery, type PageParams } from "@/domains/assess/api";

export type Membership = components["schemas"]["app__features__tenancy__schemas__MembershipRead"];
export type MembershipPage = components["schemas"]["Page_MembershipRead_"];
export type AuditEvent = components["schemas"]["AuditRead"];
export type AuditPage = components["schemas"]["Page_AuditRead_"];
export type BulkMembershipsResult = components["schemas"]["BulkMembershipsResult"];
// until regenerated: the add routes answer with `temporary_password_applied`.
export type SeatedMembership = Membership & WithTemporaryPassword;
export type SkippedMembership = components["schemas"]["SkippedMembership"];

export function listMemberships(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
): Promise<MembershipPage> {
  return platformRequest<MembershipPage>(`${orgPath(slug)}/memberships`, {
    signal,
    query: pageQuery(page),
  });
}

/**
 * Put somebody in the organisation by the address an administrator knows.
 *
 * An address with no account is invited: the backend creates it and emails a
 * link to choose a password, then answers `invited: true`. When that email
 * cannot be delivered, `temporaryPassword` gives a brand-new account a password
 * the administrator relays by hand (changed at first sign-in; never applied to
 * an existing account).
 */
export function inviteMember(
  slug: string,
  input: { email: string; role: string; temporaryPassword?: string },
): Promise<SeatedMembership> {
  return platformRequest<SeatedMembership>(`${orgPath(slug)}/memberships`, {
    method: "POST",
    body: {
      email: input.email,
      role: input.role,
      ...(input.temporaryPassword ? { temporary_password: input.temporaryPassword } : {}),
    },
  });
}

/**
 * A spreadsheet's worth of staff in one request.
 *
 * The browser parses the file and the API takes rows, so an import is an
 * ordinary JSON call rather than a multipart upload the server re-parses — and
 * no password is involved: an unknown address is invited and chooses its own.
 * Each row is the single act above it, so the same rules apply: a person
 * already holding that role comes back in `skipped` with `membership_exists`
 * rather than failing the other rows, which is what makes a half-recognised
 * file a list of names an administrator can act on instead of an error page.
 */
export function bulkInviteTeam(
  slug: string,
  rows: { email: string; role: string }[],
): Promise<BulkMembershipsResult> {
  return platformRequest<BulkMembershipsResult>(`${orgPath(slug)}/memberships/bulk`, {
    method: "POST",
    body: {
      memberships: rows.map((row) => ({ email: row.email, role: row.role })),
    },
  });
}

export function changeMemberRole(
  slug: string,
  membershipId: string,
  role: string,
): Promise<Membership> {
  return platformRequest<Membership>(
    `${orgPath(slug)}/memberships/${encodeURIComponent(membershipId)}`,
    { method: "PATCH", body: { role } },
  );
}

/** Revoked, not deleted: the record of who had access, and when, survives. */
export function revokeMembership(slug: string, membershipId: string): Promise<void> {
  return platformRequest<void>(
    `${orgPath(slug)}/memberships/${encodeURIComponent(membershipId)}/revoke`,
    { method: "POST" },
  );
}

export function restoreMembership(slug: string, membershipId: string): Promise<void> {
  return platformRequest<void>(
    `${orgPath(slug)}/memberships/${encodeURIComponent(membershipId)}/restore`,
    { method: "POST" },
  );
}

/** Send the choose-a-password link again, as a new token. */
export function resendInvitation(
  slug: string,
  membershipId: string,
): Promise<{ email: string; invited_to: string }> {
  return platformRequest<{ email: string; invited_to: string }>(
    `${orgPath(slug)}/memberships/${encodeURIComponent(membershipId)}/resend-invitation`,
    { method: "POST" },
  );
}

export type BulkInvitationResponse = components["schemas"]["BulkMembershipInvitationResponse"];

/**
 * The same link again, for several people in one request.
 *
 * Each row answers for itself: `sent`, `already_accepted` or `not_found`.
 */
export function resendInvitations(
  slug: string,
  membershipIds: string[],
): Promise<BulkInvitationResponse> {
  return platformRequest<BulkInvitationResponse>(
    `${orgPath(slug)}/memberships/bulk/resend-invitation`,
    { method: "POST", body: { membership_ids: membershipIds } },
  );
}

export interface AuditFilters {
  /** Exactly this person, any case. */
  actorEmail?: string | null;
  /** An action name or its prefix, such as `membership.`. */
  action?: string | null;
}

/**
 * Who added, changed or removed people and groups — the History tab.
 *
 * `actor_email` and `action` mean what they mean on `GET /platform/audit`.
 */
export function listAudit(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
  filters: AuditFilters = {},
): Promise<AuditPage> {
  return platformRequest<AuditPage>(`${orgPath(slug)}/audit`, {
    signal,
    query: {
      ...pageQuery(page),
      actor_email: filters.actorEmail?.trim() || undefined,
      action: filters.action?.trim() || undefined,
    },
  });
}
