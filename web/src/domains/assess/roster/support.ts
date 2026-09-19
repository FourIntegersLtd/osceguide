import type { Trainee } from "@/domains/assess/api";
import type { Cohort } from "@/domains/assess/roster/api";

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
  if (!cohortId) return "None";
  return cohorts.find((cohort) => cohort.id === cohortId)?.name ?? "Unknown group";
}

export function accessActive(trainee: Trainee): boolean {
  return !trainee.access_revoked;
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
