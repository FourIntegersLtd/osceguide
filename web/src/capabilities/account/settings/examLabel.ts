/**
 * How an exam reads on the settings screen.
 *
 * The backend names every exam (`DashboardExam.name` / `ExamRead.name`), an
 * institution's own included, so this is a fallback for the moment before
 * that name has loaded rather than a second source of exam names.
 */
export function examLabel(name: string | null | undefined, code: string | null | undefined): string {
  if (name) return name;
  if (!code) return "No exam chosen yet";
  return code.toUpperCase();
}
