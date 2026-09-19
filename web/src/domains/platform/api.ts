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
 * its powers — which is also why the memberships list and the audit log, both
 * `OrgAdmin`, are not readable from here at all. See `docs/port-gaps.md`.
 */
import { platformRequest, type components } from "@/foundation/platform-client";

type S = components["schemas"];

export type Overview = S["PlatformOverview"];
export type Organization = S["OrganizationRead"];
export type OrganizationPage = S["Page_OrganizationRead_"];
export type User = S["UserSummary"];
export type UserPage = S["Page_UserSummary_"];
export type Membership = S["app__features__tenancy__schemas__MembershipRead"];

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

export function listOrganizations(
  options: { status?: string | null } & PageParams = {},
  signal?: AbortSignal,
): Promise<OrganizationPage> {
  return platformRequest<OrganizationPage>(`${PLATFORM}/organizations`, {
    signal,
    query: { ...pageQuery(options), status: options.status ?? undefined },
  });
}

/**
 * Every organisation, status filter applied by the backend.
 *
 * The directory is searched and grouped in the browser — by name, by slug and
 * by type — because the endpoint takes `status`, `cursor` and `limit` and
 * nothing else. That is fine at this size and stops being fine in the
 * thousands; `docs/port-gaps.md` says so.
 */
export function listAllOrganizations(
  status?: string | null,
  signal?: AbortSignal,
): Promise<Organization[]> {
  return collectPages((cursor) => listOrganizations({ status, cursor }, signal));
}

/** One organisation. The org-scoped read, which admits a platform admin. */
export function readOrganization(slug: string, signal?: AbortSignal): Promise<Organization> {
  return platformRequest<Organization>(`/api/v1/orgs/${encodeURIComponent(slug)}`, { signal });
}

export function searchUsers(
  options: { q?: string | null } & PageParams = {},
  signal?: AbortSignal,
): Promise<UserPage> {
  return platformRequest<UserPage>(`${PLATFORM}/users`, {
    signal,
    query: { ...pageQuery(options), q: options.q?.trim() || undefined },
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
 * No password passes through this app. An address with no account is invited
 * and the backend emails a link; the retiring console generated a temporary
 * password in the browser for an administrator to relay by hand.
 */
export function seatMembership(
  slug: string,
  input: { email: string; role: string },
): Promise<Membership> {
  return platformRequest<Membership>(`${orgs(slug)}/memberships`, {
    method: "POST",
    body: { email: input.email, role: input.role },
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
