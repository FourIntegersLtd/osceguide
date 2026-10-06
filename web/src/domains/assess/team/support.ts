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
