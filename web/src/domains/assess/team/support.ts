import type { Membership } from "@/domains/assess/team/api";
import { isAdminRole } from "@/foundation/session/roles";

/**
 * The roles a screen may offer, and what they are called.
 *
 * `owner` and the two tenant-shaped roles (`institution_admin`,
 * `partner_admin`) are displayed but never offered: the backend's
 * `ORG_ADMIN_ROLES` accepts them, and an owner is created with the
 * organisation rather than invited into it.
 */
export const ASSIGNABLE_ROLES = ["supervisor", "admin"] as const;

export type AssignableRole = (typeof ASSIGNABLE_ROLES)[number];

export function isOwner(member: Membership): boolean {
  return (member.role ?? "").toLowerCase() === "owner";
}

export function isActive(member: Membership): boolean {
  return member.status !== "revoked" && !member.revoked_at;
}

/** Active first, then admins above supervisors, then by address. */
export function sortMembers(members: Membership[]): Membership[] {
  const rank = (member: Membership) => {
    if (isOwner(member)) return 0;
    if (isAdminRole(member.role)) return 1;
    return 2;
  };
  return [...members].sort((a, b) => {
    if (isActive(a) !== isActive(b)) return isActive(a) ? -1 : 1;
    if (rank(a) !== rank(b)) return rank(a) - rank(b);
    return (a.email ?? "").localeCompare(b.email ?? "");
  });
}

/** Who a bulk revoke may name: active people other than the owner (the server also skips the last admin). */
export function revokableStaff(rows: Membership[]): Membership[] {
  return rows.filter((member) => isActive(member) && !isOwner(member));
}

export function staffRevokeTitle(count: number): string {
  return `Revoke access for ${count} staff ${count === 1 ? "member" : "members"}?`;
}

/** The change-role box's one-line explanation of the two roles it offers. */
export const ROLE_CHOICE_HELP =
  "Supervisor: runs circuits and marks the candidates on them. Admin: also manages the team and the organisation's settings, and signs off results.";

/** "4 staff accounts" — the count the old members card carried. */
export function staffCountLabel(count: number): string {
  return `${count} staff account${count === 1 ? "" : "s"}`;
}

/** The old header's subtitle, which changed with the tab. */
export function sectionSubtitle(section: "members" | "invite" | "activity"): string {
  switch (section) {
    case "members":
      return "Who can run circuits and sign off results in this organisation.";
    case "invite":
      return "Invite a supervisor or an admin by email.";
    case "activity":
      return "Who added, changed, or removed people and groups.";
  }
}
