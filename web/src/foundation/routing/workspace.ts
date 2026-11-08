/**
 * A workspace is where a person is standing.
 *
 * `platform-api` has no notion of product arms. It has exams, organisations
 * with a `org_type`, entitlements and one `attempts` table. A person's own
 * practice and an institution they belong to are the same kind of thing seen
 * from two sides, so they are addressed the same way: `/app/me` and
 * `/app/kings`.
 *
 * That is deliberate and it is what ADR 0002 argues. GitHub, Linear, Vercel
 * and Notion all address a personal space and a team space with one grammar;
 * the alternative — consumer pages at the site root, organisations behind a
 * prefix — forces a special case into every routing decision and produced the
 * two defects that prompted this: signing in always landed an org member on
 * the institution arm, and there was no way back to their own practice.
 */

/** The slug that means "my own practice". No organisation may take it. */
export const PERSONAL_SLUG = "me";

/**
 * Slugs an organisation may never use, because a route or a workspace already
 * means something by that name.
 */
export const RESERVED_SLUGS: readonly string[] = [
  PERSONAL_SLUG,
  "app",
  "staff",
  "login",
  "register",
  "api",
  "new",
  "settings",
];

/**
 * What an organisation is for, as the backend spells it.
 *
 * `tenancy/schemas.py` accepts `institution | partner | employer` when an organisation is
 * created. An unknown stored value is still handled rather than crashing, see
 * `workspaceKind`.
 */
export type OrgType = "institution" | "partner" | "employer";

export type WorkspaceKind = "personal" | OrgType;

export interface PersonalWorkspace {
  kind: "personal";
  slug: typeof PERSONAL_SLUG;
  name: string;
  /** Always null: a personal workspace has no organisation behind it. */
  orgSlug: null;
  role: null;
}

export interface OrgWorkspace {
  kind: OrgType;
  slug: string;
  name: string;
  orgSlug: string;
  role: string;
}

export type Workspace = PersonalWorkspace | OrgWorkspace;

export function isPersonal(workspace: Workspace): workspace is PersonalWorkspace {
  return workspace.kind === "personal";
}

export const PERSONAL_WORKSPACE: PersonalWorkspace = {
  kind: "personal",
  slug: PERSONAL_SLUG,
  name: "Training",
  orgSlug: null,
  role: null,
};

/**
 * An organisation's `org_type`, narrowed, with an unknown value treated as an
 * institution.
 *
 * A value the frontend has not heard of must not blank the screen. An
 * institution is the safe reading: it is the most restrictive shell and the
 * backend's own default (`server_default='institution'`).
 */
export function workspaceKind(orgType: string | null | undefined): OrgType {
  return orgType === "partner" || orgType === "employer" ? orgType : "institution";
}

/** Where a workspace's screens live. */
export function workspaceBasePath(workspace: Workspace | string): string {
  const slug = typeof workspace === "string" ? workspace : workspace.slug;
  return `/app/${slug}`;
}

/** Whether a slug could address a workspace at all. Used before a lookup. */
export function isWorkspaceSlug(value: string): boolean {
  return /^[a-z0-9][a-z0-9-]{0,62}$/.test(value);
}
