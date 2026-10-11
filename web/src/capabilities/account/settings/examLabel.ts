/** What stands where an exam would be when none is chosen. */
export const NO_EXAM_LABEL = "No exam chosen yet";

/** "Simulated Consultation Assessment" -> "SCA". */
function initialism(name: string): string {
  return name
    .split(/\s+/)
    .map((word) => word[0] ?? "")
    .join("")
    .toUpperCase();
}

/**
 * How an exam reads on the settings screen: the name, with the code in brackets
 * when the code is that name's initials (`Simulated Consultation Assessment (SCA)`),
 * since a candidate knows the exam by either.
 *
 * The backend names every exam (`DashboardExam.name` / `ExamRead.name`), an
 * institution's own included, so the code alone is a fallback for the moment
 * before that name has loaded rather than a second source of exam names.
 */
export function examLabel(name: string | null | undefined, code: string | null | undefined): string | null {
  const upper = code?.toUpperCase();
  if (name) return upper && initialism(name) === upper ? `${name} (${upper})` : name;
  return upper || null;
}
