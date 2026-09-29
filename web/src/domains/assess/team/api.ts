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
import { collectPages, orgPath, pageQuery, type PageParams } from "@/domains/assess/api";

export type Membership = components["schemas"]["app__features__tenancy__schemas__MembershipRead"];
export type MembershipPage = components["schemas"]["Page_MembershipRead_"];
export type AuditEvent = components["schemas"]["AuditRead"];
export type AuditPage = components["schemas"]["Page_AuditRead_"];
export type BulkMembershipsResult = components["schemas"]["BulkMembershipsResult"];
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

/** Every membership, revoked ones included — the screen shows both. */
export function listAllMemberships(slug: string, signal?: AbortSignal): Promise<Membership[]> {
  return collectPages((cursor) => listMemberships(slug, signal, { cursor }));
}

/**
 * Put somebody in the organisation by the address an administrator knows.
 *
 * An address with no account is invited: the backend creates it and emails a
 * link to choose a password, then answers `invited: true`. The old client
 * generated a temporary password in the browser and displayed it for an
 * administrator to relay by hand; no password passes through this app at all.
 */
export function inviteMember(
  slug: string,
  input: { email: string; role: string },
): Promise<Membership> {
  return platformRequest<Membership>(`${orgPath(slug)}/memberships`, {
    method: "POST",
    body: { email: input.email, role: input.role },
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

/** Who added, changed or removed people and groups — the History tab. */
export function listAudit(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
): Promise<AuditPage> {
  return platformRequest<AuditPage>(`${orgPath(slug)}/audit`, { signal, query: pageQuery(page) });
}
