import type { Appeal } from "@/domains/assess/results/api";

/** Roles the server counts as an organisation administrator, and so as able to be a second marker. */
const ADMIN_ROLES = ["owner", "admin", "institution_admin"];

/** An appeal's status in the words a staff member reads. */
export function appealStatusLabel(status: string): string {
  switch (status) {
    case "open":
      return "Waiting for a second marker";
    case "in_review":
      return "With the second marker";
    case "resolved":
      return "Re-marked";
    case "declined":
      return "Declined";
    default:
      return status;
  }
}

/** What the candidate reads about their own request. */
export function candidateAppealLine(status: string): string {
  switch (status) {
    case "open":
    case "in_review":
      return "Your request is with the organisation. We email you when there is an answer.";
    case "resolved":
      return "Your result was reviewed. The outcome above is the new one.";
    case "declined":
      return "Your request was reviewed and the result stands.";
    default:
      return status;
  }
}

/** Whether the appeal is still waiting for an answer. */
export function appealIsLive(appeal: Pick<Appeal, "status">): boolean {
  return appeal.status === "open" || appeal.status === "in_review";
}

/** A team member as the second-marker picker needs them. */
export interface MarkerChoice {
  userId: string;
  label: string;
}

/**
 * Who may be named second marker: a live administrator who did not sign off or release the result.
 * The server enforces both; the picker only avoids offering what it will refuse.
 */
export function secondMarkerChoices(
  members: readonly { user_id: string; email?: string | null; role: string; revoked_at?: string | null }[],
  appeal: Pick<Appeal, "original_marker_ids">,
): MarkerChoice[] {
  const barred = new Set(appeal.original_marker_ids ?? []);
  return members
    .filter((member) => !member.revoked_at && ADMIN_ROLES.includes(member.role) && !barred.has(member.user_id))
    .map((member) => ({ userId: member.user_id, label: member.email ?? "Administrator" }));
}

/** The retention choices an administrator is offered, in days; `null` keeps everything. */
export const RETENTION_CHOICES: readonly { days: number | null; label: string }[] = [
  { days: 90, label: "90 days" },
  { days: 365, label: "1 year" },
  { days: null, label: "Keep until I delete them" },
];

/** The choice that matches what the organisation holds now, or "custom" for a value set outside this screen. */
export function retentionChoiceKey(days: number | null | undefined): string {
  const found = RETENTION_CHOICES.find((choice) => choice.days === (days ?? null));
  return found ? String(found.days) : "custom";
}

/** Whether what was typed is the candidate's address, as the server will compare it (case aside). */
export function erasureConfirmed(typed: string, email: string | null | undefined): boolean {
  return !!email && typed.trim().toLowerCase() === email.trim().toLowerCase();
}
