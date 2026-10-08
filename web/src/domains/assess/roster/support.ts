import type { Trainee } from "@/domains/assess/api";
import type { Cohort } from "@/domains/assess/roster/api";
import { errorMessage } from "@/foundation/hooks/useAsync";
import { hasCode, retryAfterPhrase } from "@/foundation/platform-client";

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

export function traineeCountLabel(count: number): string {
  return `${count} trainee${count === 1 ? "" : "s"}`;
}

/** The header subtitle, which changed with the tab in the old client. */
export function sectionSubtitle(
  section: "trainees" | "add" | "groups" | "access",
  counts: { trainees: number; groups: number },
): string {
  switch (section) {
    case "trainees":
      return "Everyone your organisation examines.";
    case "add":
      return counts.trainees === 0
        ? "Add the people who will sit your exams or training sessions."
        : "Add people one at a time, or import a spreadsheet.";
    case "groups":
      return counts.groups === 0
        ? "Sort trainees into groups like intakes or rotation teams."
        : "Cohorts are an intake; groups are who you put on a circuit.";
    case "access":
      return "Give a trainee access to an exam they can practise between sittings.";
  }
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

export type RosterTabKey = "trainees" | "add" | "groups" | "access";

/**
 * The roster's tabs. Exam access is the org admin's: its list and grants are closed to a
 * supervisor by the API, so the tab is not offered to one.
 */
export function rosterTabs(canManage: boolean): { key: RosterTabKey; label: string }[] {
  const tabs: { key: RosterTabKey; label: string }[] = [
    { key: "trainees", label: "Everyone" },
    { key: "add", label: "Add people" },
    { key: "groups", label: "Groups" },
  ];
  return canManage ? [...tabs, { key: "access", label: "Exam access" }] : tabs;
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
  if (hasCode(cause, "too_many_requests")) {
    const wait = retryAfterPhrase(cause);
    return `You have sent a lot of invitation emails just now. ${wait ? `Try again in ${wait}.` : "Wait a while, then try again."}`;
  }
  return errorMessage(cause);
}
