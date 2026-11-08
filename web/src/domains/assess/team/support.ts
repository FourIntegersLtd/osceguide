import { plural } from "@/foundation/format";
import type { Membership } from "@/domains/assess/team/api";
import { isAdminRole, ROLE_DESCRIPTIONS } from "@/foundation/session/roles";
import { isPlatformError } from "@/foundation/platform-client";
import { roleLabel } from "@/foundation/session/roles";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

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

/** What the invite form and the change-role box offer: an employer also has a lead assessor. */
export type TeamRole = AssignableRole | "gp_lead";

export function assignableRoles(w: Pick<AssessWords, "hiring">): readonly TeamRole[] {
  return w.hiring ? ["supervisor", "gp_lead", "admin"] : ASSIGNABLE_ROLES;
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
  "That would leave the organisation with no admin, so no one was removed. Keep at least one admin, or make someone else an admin first.";

/** What to tell the user when a bulk revoke fails: `last_admin` is the whole batch refused. */
export function bulkRevokeFailure(cause: unknown, fallback: string): string {
  return isPlatformError(cause) && cause.code === "last_admin" ? LAST_ADMIN_MESSAGE : fallback;
}

/** "Resent 2 of 3 invitations." */
export function resendSummary(results: { outcome: string }[]): string {
  const sent = results.filter((result) => result.outcome === "sent").length;
  return `Resent ${sent} of ${results.length} invitations.`;
}

function staffRevokeTitle(count: number): string {
  return `Revoke access for ${plural(count, "staff member")}?`;
}

/** The change-role box's one-line explanation of the two roles it offers. */
const lower = (text: string | undefined) => (text ?? "").replace(/^./, (c) => c.toLowerCase());
export const ROLE_CHOICE_HELP = `Supervisor: ${lower(ROLE_DESCRIPTIONS.supervisor)} Admin: also ${lower(ROLE_DESCRIPTIONS.admin)}`;

/** "4 staff accounts" — the count the old members card carried. */
export function staffCountLabel(count: number): string {
  return plural(count, "staff account");
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
function revokeLead(email: string | null | undefined, isSelf: boolean): string {
  if (isSelf) {
    return "You are revoking your own access. You will be signed out of this organisation straight away and only another admin can restore you. Nothing you have marked is deleted.";
  }
  return `${email ?? "This person"} will lose access to this organisation. Nothing they have marked is deleted.`;
}

type TeamWords = Pick<AssessWords, "hiring" | "LeadSupervisor" | "supervisor" | "supervisors" | "Supervisor" | "Supervisors" | "circuits" | "Circuits" | "trainees">;

/**
 * A membership role in the workspace's words. The api keeps `admin` and `supervisor`; an employer
 * reads Administrator and Assessor. An institution gets `roleLabel` unchanged.
 */
export function staffRoleLabel(role: string | null | undefined, w: Pick<TeamWords, "hiring" | "Supervisor" | "LeadSupervisor">): string {
  if (!w.hiring) return roleLabel(role);
  switch ((role ?? "").toLowerCase()) {
    case "admin":
    case "institution_admin":
    case "partner_admin":
      return "Administrator";
    case "supervisor":
      return w.Supervisor;
    case "gp_lead":
      return w.LeadSupervisor;
    default:
      return roleLabel(role);
  }
}

const HIRE_ROLE_HELP = "Assessors mark and run rotations. Administrators also manage exams, candidates and billing.";
const HIRE_LEAD_HELP = "A lead assessor settles disagreements between two assessors on the same station.";

/** The one-line help under a role choice: both roles in a change-role box, or the one chosen. */
export function roleHelp(w: TeamWords, role?: string): string {
  if (!w.hiring) return role ? (ROLE_DESCRIPTIONS[role] ?? "") : ROLE_CHOICE_HELP;
  return role === "gp_lead" ? HIRE_LEAD_HELP : HIRE_ROLE_HELP;
}

/** `last_admin` for an employer: the board's line, in its words. */
const HIRE_LAST_ADMIN_MESSAGE = "You are the only administrator. Make someone else an administrator before you change or remove an administrator.";

export function lastAdminMessage(w: Pick<TeamWords, "hiring">): string {
  return w.hiring ? HIRE_LAST_ADMIN_MESSAGE : LAST_ADMIN_MESSAGE;
}

/** Joined/Invited/Removed beside a person: the three states of the Assessors board. */
export function assessorStatus(member: Membership): { label: "Active" | "Invited" | "Removed"; tone: "ok" | "warn" | "neutral" } {
  if (!isActive(member)) return { label: "Removed", tone: "neutral" };
  if (isAwaitingInvite(member)) return { label: "Invited", tone: "warn" };
  return { label: "Active", tone: "ok" };
}

/** The words that differ between a staff list and an assessors list. Institution values are today's, byte for byte. */
export function teamCopy(w: TeamWords) {
  return w.hiring
    ? {
        search: "Search assessors…",
        searchAria: "Search assessors",
        loading: "Loading assessors…",
        noMatch: (query: string) => `No assessors match \u201c${query}\u201d.`,
        emptyTitle: "No assessors yet",
        emptyBody: "Invite an assessor so somebody can run a rotation.",
        invite: "Invite an assessor",
        person: "Person",
        led: "Rotations led",
        access: "Status",
        revoked: "Removed",
        revoke: "Remove access",
        revoking: "Removing…",
        revokeBulk: (count: number) => `Remove access for ${count} ${count === 1 ? "person" : "people"}?`,
        revokeBulkLead: "These people will no longer be able to sign in to this organisation. Their marking is kept. The owner, you and the last administrator are left out of the selection, and an organisation always keeps at least one administrator.",
        bulkDone: (done: number, all: number) => `Access removed for ${done} of ${all} assessors.`,
        count: (n: number) => `${n} ${n === 1 ? "person" : "people"}`,
        revokeOne: (email: string | null | undefined, isSelf: boolean) =>
          isSelf
            ? "You are removing your own access. You will be signed out of this organisation straight away and only another administrator can restore you. Nothing you have marked is deleted."
            : `${email ?? "This person"} will lose access to this organisation. Nothing they have marked is deleted.`,
        readOnly: `${w.Supervisor} (read only)`,
        inviteOnlyAdmin: "Only an administrator can invite assessors",
        inviteTitle: "Invite an assessor",
        inviteHelp: HIRE_ROLE_HELP,
        send: "Send invitation",
        sheetHelp: "Upload a list of assessors saved from Excel or Google Sheets as a .csv file. Anyone already on the list is skipped and shown to you.",
        auditEmpty: "Invitations, role changes and candidate edits appear here as they happen.",
      }
    : {
        search: "Search staff…",
        searchAria: "Search staff",
        loading: "Loading staff…",
        noMatch: (query: string) => `No staff match \u201c${query}\u201d.`,
        emptyTitle: "No staff yet",
        emptyBody: "Invite a supervisor so somebody can run a circuit.",
        invite: "Invite staff",
        person: "Email",
        led: "Circuits led",
        access: "Access",
        revoked: "● Revoked",
        revoke: "Revoke",
        revoking: "Revoking…",
        revokeBulk: staffRevokeTitle,
        revokeBulkLead: "These people will no longer be able to sign in to this organisation. Their marking is kept. The owner, you and the last admin are left out of the selection, and an organisation always keeps at least one admin.",
        bulkDone: (done: number, all: number) => `Access removed for ${done} of ${all} staff.`,
        count: staffCountLabel,
        revokeOne: revokeLead,
        readOnly: "Supervisor (read only)",
        inviteOnlyAdmin: "Only an owner or admin can invite staff",
        inviteTitle: "Invite someone to the team",
        inviteHelp: "Supervisors run circuits and mark them. Admins also manage the team and sign off results.",
        send: "+ Add person",
        sheetHelp: "Upload a list of staff saved from Excel or Google Sheets as a .csv file. Anyone already on the team is skipped and shown to you.",
        auditEmpty: "Invitations, role changes and roster edits appear here as they happen.",
      };
}
