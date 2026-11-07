import type { Membership } from "@/domains/assess/team/api";
import type { AssessWords } from "@/domains/assess/vocabulary";
import { isAdminRole, roleLabel, ROLE_DESCRIPTIONS } from "@/foundation/session/roles";
import { isPlatformError } from "@/foundation/platform-client";

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

/** A role as this workspace says it: an employer's supervisors are assessors and its admins lead assessors. */
export function teamRoleLabel(role: string | null | undefined, words: AssessWords): string {
  if (!words.hiring) return roleLabel(role);
  const key = (role ?? "").toLowerCase();
  if (key === "supervisor") return words.Supervisor;
  if (key === "admin" || key === "institution_admin") return `Lead ${words.supervisor}`;
  return roleLabel(role);
}

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

/** Somebody who has been invited and not yet chosen a password: the one a resend is for. */
export function isAwaitingInvite(member: Membership): boolean {
  return member.invited === true && isActive(member) && !isOwner(member);
}

/**
 * Who a bulk revoke may name, out of the ticked rows: active people other than the owner and
 * other than you, and never the last admin standing. The server refuses the WHOLE batch with
 * `last_admin` if it would remove the last administrator, so the screen leaves those rows out
 * (judged on the pages loaded; the 409 is still handled for the rest).
 */
export function revokableStaff(
  selected: Membership[],
  everyone: Membership[],
  selfUserId: string | null | undefined,
): Membership[] {
  const candidates = selected.filter(
    (member) => isActive(member) && !isOwner(member) && member.user_id !== selfUserId,
  );
  const going = new Set(candidates.map((member) => member.id));
  const adminStays = everyone.some(
    (member) => isActive(member) && isAdminRole(member.role) && !going.has(member.id),
  );
  return adminStays ? candidates : candidates.filter((member) => !isAdminRole(member.role));
}

export const LAST_ADMIN_MESSAGE =
  "That would leave the organisation with no admin, so nobody was revoked. Keep at least one admin, or make someone else an admin first.";

/** What to tell the user when a bulk revoke fails: `last_admin` is the whole batch refused. */
export function bulkRevokeFailure(cause: unknown, fallback: string): string {
  return isPlatformError(cause) && cause.code === "last_admin" ? LAST_ADMIN_MESSAGE : fallback;
}

/** "Resent 2 of 3 invitations." */
export function resendSummary(results: { outcome: string }[]): string {
  const sent = results.filter((result) => result.outcome === "sent").length;
  return `Resent ${sent} of ${results.length} invitations.`;
}

export function staffRevokeTitle(count: number): string {
  return `Revoke access for ${count} staff ${count === 1 ? "member" : "members"}?`;
}

/** One role's line of help: an employer's supervisor runs rotations, not circuits. */
export function roleDescription(role: string, words: AssessWords): string {
  if (words.hiring && role === "supervisor") return `Runs ${words.circuits} and marks ${words.trainees}.`;
  return ROLE_DESCRIPTIONS[role] ?? "";
}

/** The change-role box's one-line explanation of the two roles it offers. */
const lower = (text: string | undefined) => (text ?? "").replace(/^./, (c) => c.toLowerCase());
export function roleChoiceHelp(words: AssessWords): string {
  const runs = words.hiring ? `runs ${words.circuits} and marks ${words.trainees}.` : lower(ROLE_DESCRIPTIONS.supervisor);
  return `${teamRoleLabel("supervisor", words)}: ${runs} ${teamRoleLabel("admin", words)}: also ${lower(ROLE_DESCRIPTIONS.admin)}`;
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

/** The single-revoke dialog's line: revoking yourself ends your own access at once, so it says so. */
export function revokeLead(email: string | null | undefined, isSelf: boolean): string {
  if (isSelf) {
    return "You are revoking your own access. You will be signed out of this organisation straight away and only another admin can restore you. Nothing you have marked is deleted.";
  }
  return `${email ?? "This person"} will lose access to this organisation. Nothing they have marked is deleted.`;
}
