const EXAMS = ["sca", "plab", "casc", "ortho"] as const;

/** The four consumer exams, exported so a selector cannot drift from this list. */
export const EXAM_CODES = EXAMS;

export const EXAM_SELECTION_EVENT = "osceguide:exam-selection";
export function normalizeExamCode(value: string | null | undefined): string | null {
  const code = value?.trim().toLowerCase();
  return code && EXAMS.some((exam) => exam === code) ? code : null;
}
export function examAuthHref(path: string, exam: string | null): string {
  const code = normalizeExamCode(exam);
  return code ? `${path}?appType=${encodeURIComponent(code)}` : path;
}
export function readExamSelection(userId: string): string | null {
  try { return normalizeExamCode(localStorage.getItem(`osceguide.exam.${userId}`)); }
  catch { return null; }
}
/** A display preference; all access checks remain on the API. */
export function rememberExamSelection(userId: string, exam: string | null) {
  const code = normalizeExamCode(exam);
  if (!code) return;
  try { localStorage.setItem(`osceguide.exam.${userId}`, code); } catch { /* Storage is optional. */ }
  window.dispatchEvent(new Event(EXAM_SELECTION_EVENT));
}
