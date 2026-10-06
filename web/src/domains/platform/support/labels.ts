/**
 * Words for the codes the staff console reads back from the API.
 *
 * Roles, audit actions, job names and message sources arrive as identifiers
 * (`institution_admin`, `membership.added`, `sweep_circuits`). A person reading
 * the console should see words; the identifiers stay what the API branches on.
 */

/** Any API identifier as words: `org.mfa_policy_changed` → "Org mfa policy changed". */
export function humanise(code: string): string {
  const words = code.replace(/[._]+/g, " ").replace(/\s+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : code;
}

const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  admin: "Administrator",
  institution_admin: "Institution administrator",
  partner_admin: "Partner administrator",
  supervisor: "Supervisor",
  trainee: "Trainee",
  practice_user: "Practice user",
};

export function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? humanise(role);
}

/** The roles worth seating a first member as. An org admin adds everyone else. */
export const SEAT_ROLES = ["owner", "admin", "institution_admin", "partner_admin"] as const;

/** Every role the server's `GRANTABLE_ROLES` admits, in the order a menu offers them. */
export const MEMBER_ROLES = [...SEAT_ROLES, "supervisor", "trainee", "practice_user"] as const;

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
