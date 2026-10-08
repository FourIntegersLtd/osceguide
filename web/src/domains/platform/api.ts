/**
 * The staff console: OSCE Guide's own people, looking across every tenant.
 *
 * The one slice that reads outside an organisation. Almost everything here is
 * `/api/v1/platform/…`, which the backend keeps in a router of its own so that
 * "who may call this?" is answered by where the route lives — every one of
 * them is `PlatformAdmin`.
 *
 * The exception is `readOrganization`, and it is worth knowing why: there is
 * no `GET /platform/organizations/{slug}`, and the org-scoped read allows a
 * platform admin through on purpose (`require_org(..., allow_platform_admin)`).
 * A console admin may *read* any organisation for support and inherits none of
 * its powers. Its memberships and audit log are read through their own
 * platform-scope routes (`listOrgMembershipsForSupport`, `listOrgAuditForSupport`).
 */
import { platformRequest, type components } from "@/foundation/platform-client";

type S = components["schemas"];

export type Overview = S["PlatformOverview"];
/**
 * Contract dates may be present once the OpenAPI spec catches up with
 * platform-api. `parent_org_id` is the organisation this one sits under (a
 * deanery's trusts, say).
 */
export type Organization = S["OrganizationRead"] & {
  contract_starts_at?: string | null;
  contract_ends_at?: string | null;
};
export type OrganizationPage = S["Page_OrganizationRead_"];
export type User = S["UserSummary"];
export type UserPage = S["Page_UserSummary_"];
export type Membership = S["app__features__tenancy__schemas__MembershipRead"];
export type AuditEntry = S["AuditRead"];
export type AuditPage = S["Page_AuditRead_"];

/** Support view of one account — richer than `UserSummary`. */
export type PlatformUserDetail = S["PlatformUserDetail"] & {
  consumer_role?: string | null;
  legacy_consumer_ids?: Record<string, string>;
};

/**
 * One row of the account directory: the seven columns the retiring console
 * had, each answered by the slice that owns the fact. Served by `dashboard`
 * rather than `tenancy` because four of those slices sit above it.
 */
export type DirectoryUser = S["DirectoryUser"];
export type DirectoryPage = S["Page_DirectoryUser_"];
export type DirectorySummary = S["DirectorySummary"];
export type ExamDirectorySummary = S["ExamDirectorySummary"];

export interface UpdatePlatformUserInput {
  name?: string | null;
  exam_code?: string | null;
  status?: "active" | "deactivated" | null;
  /** `YYYY-MM-DD`. */
  exam_date?: string | null;
  needs_extra_time?: boolean | null;
  /** Seconds, 1–3659. `null` clears it back to the exam's own length. */
  custom_reading_seconds?: number | null;
  custom_simulation_seconds?: number | null;
}

/** The directory's facets. `access` is the old filter modal's three states. */
export interface DirectoryFilters {
  q?: string | null;
  examCode?: string | null;
  status?: string | null;
  access?: string | null;
  planCode?: string | null;
  /** The group under no exam heading: chose none, holds no live access. Overrides `examCode`. */
  unassigned?: boolean;
}

const PLATFORM = "/api/v1/platform";

const orgs = (slug: string) => `${PLATFORM}/organizations/${encodeURIComponent(slug)}`;

export interface PageParams {
  limit?: number;
  cursor?: string | null;
}

/** The backend caps `limit` at a hundred; asking for more is a 422. */
const PAGE_LIMIT = 100;
const MAX_PAGES = 25;

function pageQuery(page?: PageParams) {
  return { limit: page?.limit ?? PAGE_LIMIT, cursor: page?.cursor ?? undefined };
}

async function collectPages<T>(
  fetchPage: (cursor: string | null) => Promise<{ items: T[]; next_cursor?: string | null }>,
): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null = null;
  for (let index = 0; index < MAX_PAGES; index += 1) {
    const page = await fetchPage(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? null;
    if (!cursor) break;
  }
  return items;
}

/* ------------------------------------------------------------------ Reads */

export function readOverview(signal?: AbortSignal): Promise<Overview> {
  return platformRequest<Overview>(`${PLATFORM}/overview`, { signal });
}

export interface DirectoryFilters {
  status?: string | null;
  /** Name or slug fragment. */
  search?: string | null;
  orgType?: string | null;
}

export function listOrganizations(
  options: DirectoryFilters & PageParams = {},
  signal?: AbortSignal,
): Promise<OrganizationPage> {
  return platformRequest<OrganizationPage>(`${PLATFORM}/organizations`, {
    signal,
    query: {
      ...pageQuery(options),
      status: options.status ?? undefined,
      search: options.search?.trim() || undefined,
      org_type: options.orgType ?? undefined,
    },
  });
}

/**
 * Every organisation matching the filters, filtered by the backend.
 *
 * Search (name or slug) and type used to run in the browser over the whole
 * directory, walked page by page, which stops scaling in the thousands.
 */
export function listAllOrganizations(
  filters: DirectoryFilters | string | null = null,
  signal?: AbortSignal,
): Promise<Organization[]> {
  const options = typeof filters === "string" || filters === null ? { status: filters } : filters;
  return collectPages((cursor) => listOrganizations({ ...options, cursor }, signal));
}

/** One organisation. The org-scoped read, which admits a platform admin. */
export function readOrganization(slug: string, signal?: AbortSignal): Promise<Organization> {
  return platformRequest<Organization>(`/api/v1/orgs/${encodeURIComponent(slug)}`, { signal });
}

/* ---------------------------------------------------------- SSO config */

export type SsoConfig = S["SsoConfigRead"];
export type SsoBinding = S["SsoBinding"];
export type SaveSsoConfigInput = S["SaveSsoConfig"];

/**
 * One organisation's SSO arrangement.
 *
 * `GET /platform/orgs/{slug}/sso` answers 200 `null` when nothing has been set
 * up yet, which is an empty form; an unknown organisation is a 404.
 */
export function readSsoConfig(slug: string, signal?: AbortSignal): Promise<SsoConfig | null> {
  return platformRequest<SsoConfig | null>(
    `${PLATFORM}/orgs/${encodeURIComponent(slug)}/sso`,
    { signal },
  );
}

/**
 * Save the arrangement. The read returns flat `bindings`; the write takes
 * `hosts` and `email_domains` as separate lists — the service flattens them
 * back on the other side.
 */
export function saveSsoConfig(slug: string, input: SaveSsoConfigInput): Promise<SsoConfig> {
  return platformRequest<SsoConfig>(
    `${PLATFORM}/orgs/${encodeURIComponent(slug)}/sso`,
    { method: "PUT", body: input },
  );
}

/**
 * The account directory, one page of it.
 *
 * Every filter is the backend's, so a narrowed listing is exact rather than a
 * search over what happened to be paged in. Twenty-five a page: the screen
 * shows a group per exam and each group pages on its own.
 */
export function readDirectory(
  filters: DirectoryFilters & PageParams = {},
  signal?: AbortSignal,
): Promise<DirectoryPage> {
  return platformRequest<DirectoryPage>(`${PLATFORM}/directory`, {
    signal,
    query: {
      limit: filters.limit ?? 25,
      cursor: filters.cursor ?? undefined,
      q: filters.q?.trim() || undefined,
      exam_code: filters.examCode || undefined,
      status: filters.status || undefined,
      access: filters.access || undefined,
      plan_code: filters.planCode || undefined,
      unassigned: filters.unassigned ? true : undefined,
    },
  });
}

/** Per exam: how many accounts, and the paid / trial / not-started split. */
export function readDirectorySummary(signal?: AbortSignal): Promise<DirectorySummary> {
  return platformRequest<DirectorySummary>(`${PLATFORM}/directory/summary`, { signal });
}

/** One account's directory row — the facts the detail's header shows. */
export function readDirectoryUser(userId: string, signal?: AbortSignal): Promise<DirectoryUser> {
  return platformRequest<DirectoryUser>(`${PLATFORM}/directory/users/${encodeURIComponent(userId)}`, {
    signal,
  });
}

/* ----------------------------------------------------------------- Writes */

/**
 * Provision an organisation.
 *
 * `org_type` decides which console its members land in. There is no separate
 * employer product: a hiring organisation is one of these running exam-mode
 * sittings. The backend's pattern admits `institution` and `partner` only.
 */
export function provisionOrganization(input: {
  name: string;
  slug: string;
  orgType: string;
}): Promise<Organization> {
  return platformRequest<Organization>(`${PLATFORM}/organizations`, {
    method: "POST",
    body: { name: input.name, slug: input.slug, org_type: input.orgType },
  });
}

/**
 * Rename an organisation, change its type, or record its contract dates.
 *
 * Not the slug: every foreign key points at the row's id and the slug is the
 * URL, so renaming one is a redirect problem rather than a field edit.
 *
 * Only the keys present are sent — the backend excludes what was not set, so
 * sending `undefined` for a date leaves it alone and sending `null` clears it.
 * Those are different intentions and the caller has to be able to express both.
 */
export interface OrganizationChanges {
  name?: string;
  org_type?: string;
  contract_starts_at?: string | null;
  contract_ends_at?: string | null;
}

export function updateOrganization(
  slug: string,
  changes: OrganizationChanges,
): Promise<Organization> {
  return platformRequest<Organization>(orgs(slug), { method: "PATCH", body: changes });
}

/**
 * Whether this organisation's staff must sign in with a second factor (E-11).
 *
 * Its own org-scoped route (`/orgs/{slug}/mfa-policy`, which admits a platform
 * admin who is not a member), not a `/platform/…` one: requiring MFA changes who
 * can sign in at their next password login, so it is audited as its own act.
 */
export function setStaffMfaPolicy(slug: string, required: boolean): Promise<Organization> {
  return platformRequest<Organization>(`/api/v1/orgs/${encodeURIComponent(slug)}/mfa-policy`, {
    method: "PATCH",
    body: { require_staff_mfa: required },
  });
}

/** Suspended, never deleted: a tenant's rows include results that must stay defensible. */
export function suspendOrganization(slug: string): Promise<Organization> {
  return platformRequest<Organization>(`${orgs(slug)}/suspend`, { method: "POST" });
}

export function restoreOrganization(slug: string): Promise<Organization> {
  return platformRequest<Organization>(`${orgs(slug)}/restore`, { method: "POST" });
}

/**
 * Put the first person into an organisation.
 *
 * Every other membership is added by an org admin, and a freshly provisioned
 * organisation has none — so without this the console could provision, rename
 * and suspend a tenant but not seat its owner. A platform admin holds no org
 * role, which is why this is a `/platform/…` route rather than the org one.
 *
 * By default no password passes through this app: an address with no account
 * is invited and the backend emails a link. `temporaryPassword` is the fallback
 * for when that email cannot be delivered. The console admin types it and
 * relays it by hand; the backend applies it only to a brand-new account, which
 * must change it at first sign-in.
 */
export function seatMembership(
  slug: string,
  input: { email: string; role: string; temporaryPassword?: string },
): Promise<Membership> {
  return platformRequest<Membership>(`${orgs(slug)}/memberships`, {
    method: "POST",
    body: {
      email: input.email,
      role: input.role,
      ...(input.temporaryPassword ? { temporary_password: input.temporaryPassword } : {}),
    },
  });
}

/**
 * Grant or revoke the console itself.
 *
 * One route taking a boolean, rather than a grant route and a revoke route —
 * they are one decision, and two would invite one of them to be forgotten.
 */
export function setPlatformAdmin(userId: string, isPlatformAdmin: boolean): Promise<User> {
  return platformRequest<User>(
    `${PLATFORM}/users/${encodeURIComponent(userId)}/platform-admin`,
    { method: "PUT", body: { is_platform_admin: isPlatformAdmin } },
  );
}

export function readUser(userId: string, signal?: AbortSignal): Promise<PlatformUserDetail> {
  return platformRequest<PlatformUserDetail>(`${PLATFORM}/users/${encodeURIComponent(userId)}`, {
    signal,
  });
}

export function updateUser(
  userId: string,
  changes: UpdatePlatformUserInput,
): Promise<PlatformUserDetail> {
  return platformRequest<PlatformUserDetail>(`${PLATFORM}/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: changes,
  });
}

export function resetUserPassword(userId: string): Promise<void> {
  return platformRequest<void>(
    `${PLATFORM}/users/${encodeURIComponent(userId)}/reset-password`,
    { method: "POST" },
  );
}

export function listPlatformAdmins(signal?: AbortSignal): Promise<User[]> {
  return platformRequest<User[]>(`${PLATFORM}/admins`, { signal });
}

export interface PlatformAdminInviteResult {
  user: User;
  invited: boolean;
}

/** Grant the staff console by email; new accounts are invited to set a password. */
export function invitePlatformAdmin(email: string): Promise<PlatformAdminInviteResult> {
  return platformRequest<PlatformAdminInviteResult>(`${PLATFORM}/admins`, {
    method: "POST",
    body: { email },
  });
}

export function listOrgMembershipsForSupport(
  slug: string,
  page?: PageParams,
  signal?: AbortSignal,
): Promise<{ items: Membership[]; next_cursor?: string | null }> {
  return platformRequest(`${PLATFORM}/organizations/${encodeURIComponent(slug)}/memberships`, {
    signal,
    query: pageQuery(page),
  });
}

export function listOrgAuditForSupport(
  slug: string,
  page?: PageParams,
  signal?: AbortSignal,
): Promise<AuditPage> {
  return platformRequest<AuditPage>(
    `${PLATFORM}/organizations/${encodeURIComponent(slug)}/audit`,
    { signal, query: pageQuery(page) },
  );
}

/* ---------- the contact and feedback inbox ---------- */

export type SiteMessage = components["schemas"]["MessageRead"];

/**
 * Everybody's messages to us — contact form and product feedback.
 *
 * Platform admin only, because it is everybody's: a contact note from a
 * candidate may name their employer, and an organisation's own admin has no
 * business reading the messages that arrived at the platform.
 */
export type SiteMessagePage = { items: SiteMessage[]; next_cursor?: string | null };

/**
 * A page of the inbox, filtered by the server.
 *
 * `handled` narrows to open (`false`) or answered (`true`) messages; omitting
 * it reads both. This used to ask for `limit: 200` and let the "Show handled"
 * toggle hide rows in the browser, which stopped being the whole inbox as
 * soon as it passed two hundred messages.
 */
export function listSiteMessages(
  query: { kind?: string; handled?: boolean | null; cursor?: string | null; limit?: number } = {},
  signal?: AbortSignal,
): Promise<SiteMessagePage> {
  return platformRequest<SiteMessagePage>(`${PLATFORM}/site/messages`, {
    signal,
    query: {
      kind: query.kind || undefined,
      handled: query.handled ?? undefined,
      cursor: query.cursor ?? undefined,
      limit: query.limit ?? 25,
    },
  });
}

/** Answered, or read and nothing to do. Either way it leaves the queue. */
export function markMessageHandled(messageId: string): Promise<SiteMessage> {
  return platformRequest<SiteMessage>(
    `${PLATFORM}/site/messages/${encodeURIComponent(messageId)}/handled`,
    { method: "POST" },
  );
}

/**
 * Answer a message in its sender's inbox, and take it out of the queue.
 * A sender who wrote without signing in has no inbox: that is a 409 with the
 * code `message_not_repliable`, and the screen offers their email instead.
 */
export function replyToSiteMessage(messageId: string, body: string): Promise<SiteMessage> {
  return platformRequest<SiteMessage>(
    `${PLATFORM}/site/messages/${encodeURIComponent(messageId)}/reply`,
    { method: "POST", body: { body } satisfies components["schemas"]["ReplyToSiteMessage"] },
  );
}

/* ---------- notes and announcements in learners' inboxes ---------- */

export type SentInboxMessage = components["schemas"]["SentInboxMessage"];
export type Announcement = components["schemas"]["PlatformAnnouncementRead"];
export type AnnouncementPage = components["schemas"]["Page_PlatformAnnouncementRead_"];

/** A note to one person's inbox. In-app only; no email is sent. */
export function sendUserNote(
  userId: string,
  input: { subject: string; body: string },
): Promise<SentInboxMessage> {
  return platformRequest<SentInboxMessage>(
    `${PLATFORM}/users/${encodeURIComponent(userId)}/messages`,
    { method: "POST", body: input satisfies components["schemas"]["SendUserNote"] },
  );
}

/** Every announcement, withdrawn ones included, with how many people read it. */
export function listAnnouncements(
  query: { cursor?: string | null; limit?: number } = {},
  signal?: AbortSignal,
): Promise<AnnouncementPage> {
  return platformRequest<AnnouncementPage>(`${PLATFORM}/announcements`, {
    signal,
    query: { cursor: query.cursor ?? undefined, limit: query.limit ?? 25 },
  });
}

/** Tell every learner something. Reaches accounts that exist now; later sign-ups do not see it. */
export function postAnnouncement(input: { subject: string; body: string }): Promise<SentInboxMessage> {
  return platformRequest<SentInboxMessage>(`${PLATFORM}/announcements`, {
    method: "POST",
    body: input satisfies components["schemas"]["PostAnnouncement"],
  });
}

export function withdrawAnnouncement(messageId: string): Promise<Announcement> {
  return platformRequest<Announcement>(
    `${PLATFORM}/announcements/${encodeURIComponent(messageId)}/withdraw`,
    { method: "POST" },
  );
}

/* ---------- the station report queue ---------- */

export type StationFlag = components["schemas"]["StationFlagRead"];
export type StationFlagPage = components["schemas"]["Page_StationFlagRead_"];

/**
 * Every report readers have filed about a station, oldest first.
 *
 * `status` narrows to the queue (`open`) or to what has been answered. Omitting
 * it reads both, which is what makes "have we ever seen this case before?"
 * answerable from one screen rather than from the database.
 */
export function listStationFlags(
  query: { status?: string | null; cursor?: string | null } = {},
  signal?: AbortSignal,
): Promise<StationFlagPage> {
  return platformRequest<StationFlagPage>(`${PLATFORM}/station-flags`, {
    signal,
    query: { status: query.status || undefined, cursor: query.cursor || undefined, limit: 100 },
  });
}

/** Close a report with what was done about it, or put it back on the queue. */
export function decideStationFlag(
  flagId: string,
  input: { status: "open" | "resolved"; note?: string | null },
): Promise<StationFlag> {
  return platformRequest<StationFlag>(
    `${PLATFORM}/station-flags/${encodeURIComponent(flagId)}`,
    { method: "PATCH", body: { status: input.status, note: input.note ?? null } },
  );
}

/* ------------------------------------------------------ referral payouts */

export type ReferralPayout = components["schemas"]["ReferralAdminRead"];
export type ReferralPayoutPage = components["schemas"]["Page_ReferralAdminRead_"];

/**
 * The settlement queue: redeemed referrals, and whether each has been paid.
 *
 * Nothing in the product moves money — a referral is settled by bank transfer
 * outside it — so this is the record of what is owed and what has been sent.
 * Unredeemed codes are not here: an outstanding code is neither paid nor
 * unpaid.
 */
export function listReferralPayouts(
  query: { payoutStatus?: string | null; cursor?: string | null } = {},
  signal?: AbortSignal,
): Promise<ReferralPayoutPage> {
  return platformRequest<ReferralPayoutPage>("/api/v1/growth/referrals", {
    signal,
    query: {
      payout_status: query.payoutStatus || undefined,
      cursor: query.cursor || undefined,
      limit: 100,
    },
  });
}

/** Write down that a transfer was made, or take it back. */
export function setReferralPayout(
  referralId: string,
  input: { payoutStatus: "paid" | "unpaid"; payoutReference?: string | null },
): Promise<ReferralPayout> {
  return platformRequest<ReferralPayout>(
    `/api/v1/growth/referrals/${encodeURIComponent(referralId)}/payout`,
    {
      method: "POST",
      body: {
        payout_status: input.payoutStatus,
        payout_reference: input.payoutReference ?? null,
      },
    },
  );
}
