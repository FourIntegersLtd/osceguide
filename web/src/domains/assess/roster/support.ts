import type { Trainee } from "@/domains/assess/api";
import type { AssessWords } from "@/domains/assess/vocabulary";
import type { Cohort } from "@/domains/assess/roster/api";
import { errorMessage } from "@/foundation/hooks/useAsync";
import { hasCode } from "@/foundation/platform-client";

/** A trainee exists before they have ever signed in, so a name may be absent. */
export function fullName(trainee: Trainee): string | null {
  const parts = [trainee.first_name, trainee.last_name].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : null;
}

export function displayName(trainee: Trainee): string {
  return fullName(trainee) ?? trainee.email;
}

/**
 * The old roster carried a free-text `cohort` string on every trainee and
 * matched groups by comparing labels, lowercased and trimmed. The platform has
 * a cohort row with an id, so a rename is a rename rather than an orphaned
 * label on two hundred people — which is what this map replaces.
 */
export function cohortName(cohorts: Cohort[], cohortId: string | null): string {
  if (!cohortId) return "No group";
  return cohorts.find((cohort) => cohort.id === cohortId)?.name ?? "Unknown group";
}

export function accessActive(trainee: Trainee): boolean {
  return !trainee.access_revoked;
}

/**
 * Whether the screen may offer to re-send this person's invitation.
 *
 * The server says whether the account behind the row is still waiting on its
 * first use (`invitation_pending`), so an Active row that has signed in is not
 * offered a resend. A row with no account at all is offered a first invitation.
 * The backend still decides: a stale list gets `invitation_not_pending` back and
 * `TraineesPanel` retires the control for that row.
 */
export function invitationResendable(trainee: Trainee): boolean {
  return (
    accessActive(trainee) &&
    trainee.email.trim().includes("@") &&
    (trainee.invitation_pending || invitationNotAccepted(trainee))
  );
}

/** Rows a bulk invitation would reach: the ones whose invitation can be resent. */
export function awaitingInvitation(rows: Trainee[]): Trainee[] {
  return rows.filter(invitationResendable);
}

/**
 * One line for a bulk action: how many rows reached `okOutcome`, then each other
 * outcome counted, e.g. "Sent 2 of 4 invitations. 1 already signed in."
 */
export function bulkSummary(
  results: { outcome: string }[],
  okOutcome: string,
  noun: string,
): string {
  const ok = results.filter((result) => result.outcome === okOutcome).length;
  const verb = okOutcome.charAt(0).toUpperCase() + okOutcome.slice(1);
  const others = new Map<string, number>();
  for (const { outcome } of results) {
    if (outcome !== okOutcome) others.set(outcome, (others.get(outcome) ?? 0) + 1);
  }
  const rest = [...others].map(([outcome, count]) => ` ${count} ${outcome.replaceAll("_", " ")}.`);
  return `${verb} ${ok} of ${results.length} ${noun}.${rest.join("")}`;
}

/**
 * Whether a roster row still has no account behind it.
 *
 * The platform links a trainee to an account the moment they are added, so an
 * unlinked row is one a migration carried over. It is worth a word on screen —
 * that person cannot be put on a circuit yet — and the backend treats a
 * re-send for them as a first invitation rather than a refusal.
 */
export function invitationNotAccepted(trainee: Trainee): boolean {
  return trainee.user_id === null;
}

/** Active first, then by name, then by address — the old list's order. */
export function sortTrainees(trainees: Trainee[]): Trainee[] {
  return [...trainees].sort((a, b) => {
    if (accessActive(a) !== accessActive(b)) return accessActive(a) ? -1 : 1;
    return displayName(a).localeCompare(displayName(b), undefined, { sensitivity: "base" });
  });
}

export function traineeCountLabel(count: number, words: AssessWords): string {
  return `${count} ${count === 1 ? words.trainee : words.trainees}`;
}

export type TraineeStage = "added" | "invited" | "accepted" | "member" | "booked";

const STAGE_LABEL: Record<TraineeStage, string> = {
  added: "Added",
  invited: "Invited",
  accepted: "Accepted",
  member: "Member",
  booked: "Booked",
};

/**
 * Where a roster row stands between being added and sitting: the furthest step
 * reached, and, when the person looks stuck, what is wrong. Added means no
 * account yet; Invited an account nobody has used; Accepted an account in use
 * but not yet a member; Booked a place on a sitting. Revoked access is always
 * flagged. Whether practice access applies is not on the row, so it has no step.
 */
export function traineeStatus(trainee: Trainee): {
  stage: TraineeStage;
  label: string;
  attention: string | null;
} {
  const stage: TraineeStage =
    trainee.user_id === null
      ? "added"
      : trainee.invitation_pending
        ? "invited"
        : !trainee.is_member
          ? "accepted"
          : (trainee.programme_names?.length ?? 0) > 0 || trainee.stations_sat > 0
            ? "booked"
            : "member";
  let attention: string | null = null;
  if (!accessActive(trainee)) attention = "Access revoked";
  else if (stage === "added") attention = "Added, no account yet";
  else if (stage === "invited") attention = "Invited, not accepted";
  else if (stage === "accepted") attention = "Accepted, not a member";
  return { stage, label: STAGE_LABEL[stage], attention };
}

/** The trainee bulk bar's words: a cohort is a "year group"; a group is a separate list. */
export const MOVE_TO_YEAR_GROUP_LABEL = "Move to year group…";
export const NO_YEAR_GROUP_LABEL = "No year group";
export const ADD_TO_GROUP_LABEL = "Add to group…";

/** Who is in a group after adding `picked`: everyone already in it, then the new people. */
export function addToGroupIds(existing: string[], picked: string[]): string[] {
  return [...new Set([...existing, ...picked])];
}

/** The cohort delete prompt: how many sittings it detaches (they are kept, with no cohort). */
export function cohortDeleteLead(name: string, sittingCount: number): string {
  const held =
    sittingCount <= 0
      ? "No sittings are held for it."
      : `The ${sittingCount} sitting${sittingCount === 1 ? "" : "s"} held for it ${sittingCount === 1 ? "is" : "are"} kept but no longer belong to any year group.`;
  return (
    `Delete “${name}”? Nobody can be put into it afterwards. This cannot be undone, and a year group ` +
    `that still has trainees in it is not deleted. ${held}`
  );
}

/** The delete prompt. Someone who has sat stations most likely has a decision, which delete refuses. */
export function deleteLead(name: string, stationsSat: number): string {
  const base = "You can only delete a trainee with no results recorded. If they have been examined, remove their access instead.";
  if (stationsSat <= 0) return base;
  const stations = `${stationsSat} station${stationsSat === 1 ? "" : "s"}`;
  return `${name} has sat ${stations}, so deleting is likely to be refused once a result is decided. Revoke their access instead to keep their records.`;
}

/** What to tell an admin whose add or resend was refused: the two answers they can act on, said plainly. */
export function rosterErrorMessage(cause: unknown, email: string): string {
  if (hasCode(cause, "trainee_exists")) return `${email} is already on this roster.`;
  return errorMessage(cause);
}
