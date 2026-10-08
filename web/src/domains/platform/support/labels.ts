/**
 * Words for the codes the staff console reads back from the API.
 *
 * Roles, audit actions, job names and message sources arrive as identifiers
 * (`institution_admin`, `membership.added`, `sweep_circuits`). A person reading
 * the console should see words; the identifiers stay what the API branches on.
 */

import { humanise } from "@/foundation/format";
import { roleLabel } from "@/foundation/session/roles";
import { hasCode, validationFields } from "@/foundation/platform-client";

/**
 * The roles worth seating a first member as: the tenant-shaped admin. An owner
 * is created with the organisation and an org admin adds everyone else.
 */
export const SEAT_ROLES = ["institution_admin", "partner_admin"] as const;

/** Every role the server's `GRANTABLE_ROLES` admits, in the order a menu offers them. */
export const MEMBER_ROLES = [
  "owner",
  "admin",
  ...SEAT_ROLES,
  "supervisor",
  "trainee",
  "practice_user",
] as const;

/**
 * One option per distinct label: the admin roles read alike, so a menu offers
 * the first of `prefer` that is present (else the first listed) and no twin.
 */
export function oneOptionPerLabel(roles: readonly string[], prefer: readonly string[] = []): string[] {
  const rank = (role: string) => {
    const at = prefer.indexOf(role);
    return at < 0 ? prefer.length : at;
  };
  const out: string[] = [];
  for (const role of roles) {
    const twin = out.findIndex((kept) => roleLabel(kept) === roleLabel(role));
    const kept = out[twin];
    if (kept === undefined) out.push(role);
    else if (rank(role) < rank(kept)) out[twin] = role;
  }
  return out;
}

/** Roles that only make sense in one kind of organisation. */
const ROLE_ORG_TYPE: Record<string, string> = {
  institution_admin: "institution",
  trainee: "institution",
  partner_admin: "partner",
  practice_user: "partner",
};

/**
 * The roles a menu offers for an organisation of this type.
 *
 * Display only, so nobody is offered a partner administrator in a hospital:
 * the server checks every grant (`_guard_role_grant`) and stays the authority.
 */
export function rolesForOrgType(roles: readonly string[], orgType: string): string[] {
  return roles.filter((role) => {
    const only = ROLE_ORG_TYPE[role];
    return only === undefined || only === orgType;
  });
}

/** An audit row's or a job's details, as "Status: Active · Reason: …", without the empty ones. */
export function formatDetail(meta: Record<string, unknown> | null | undefined): string {
  if (!meta) return "";
  return Object.entries(meta)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${humanise(key)}: ${detailValue(value)}`)
    .join(" · ");
}

function detailValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  // A bare code such as `active` or `interaction_complete` reads as words; free text is left alone.
  if (typeof value === "string" && /^[a-z]+(?:_[a-z]+)*$/.test(value)) return humanise(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** A background task's name: the function, not its module path. */
export function jobTaskLabel(taskName: string): string {
  return humanise(taskName.split(".").pop() ?? taskName);
}

const MESSAGE_SOURCES: Record<string, string> = {
  "messages-screen": "In-app message",
  contact: "Contact form",
  "landing/help-us-improve": "Website feedback form",
  session: "After a session",
  milestone: "At a milestone",
};

/** Where a message was sent from; an unknown source is shown as it came. */
export function messageSourceLabel(source: string): string {
  return MESSAGE_SOURCES[source] ?? source;
}

/** The live badge: while reconnecting, say how old the figures still on screen are. */
export function liveFeedLabel(
  connected: boolean,
  lastFrameAt: Date | null,
): { tone: "success" | "warning"; text: string } {
  if (connected) return { tone: "success", text: "Live" };
  if (!lastFrameAt) return { tone: "warning", text: "Reconnecting" };
  const time = lastFrameAt.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return { tone: "warning", text: `Reconnecting · figures from ${time}` };
}

/** Provisioning refusals that belong to one field: the API's 422s, and a slug another organisation holds. */
export function provisionFieldErrors(cause: unknown): Record<string, string> {
  if (hasCode(cause, "org_slug_taken")) return { slug: cause.message };
  return validationFields(cause);
}
