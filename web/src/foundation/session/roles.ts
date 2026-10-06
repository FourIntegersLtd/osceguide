/**
 * What each membership role is called, wherever a screen names one: the staff
 * console, Team and the results. Display only; a permission is never read from
 * a role (`can(session, …)` is the server's answer).
 *
 * The three admin roles read alike on purpose. There is one reviewer role, the
 * admin, and a review is labelled by who writes it.
 */
export const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  admin: "Admin",
  institution_admin: "Admin",
  partner_admin: "Admin",
  supervisor: "Supervisor",
  trainee: "Trainee",
  practice_user: "Practice user",
};

/** What a role can do, in a line (mirrors the backend's role sets in `tenancy/domain.py`). */
export const ROLE_DESCRIPTIONS: Record<string, string> = {
  owner: "Runs the organisation, including its team and settings; can sign off and release results.",
  admin: "Manages the team and the organisation's settings, and signs off results.",
  institution_admin: "Runs exams and the team; can sign off and release results.",
  partner_admin: "Runs a practice partner's learners and attribution; cannot sign off or release results.",
  supervisor: "Runs circuits and marks the candidates on them.",
};

/** A role as words. An unknown role is shown as it came, or as `fallback`. */
export function roleLabel(role: string | null | undefined, fallback?: string): string {
  return ROLE_LABELS[(role ?? "").toLowerCase()] ?? fallback ?? role ?? "Member";
}

/** The backend's `ORG_ADMIN_ROLES`, read only to display (sort, label), never to gate. */
const ADMIN_ROLES = new Set(["owner", "admin", "institution_admin", "partner_admin"]);

export function isAdminRole(role: string | null | undefined): boolean {
  return ADMIN_ROLES.has((role ?? "").toLowerCase());
}
