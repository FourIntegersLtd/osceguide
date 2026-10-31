const EXAMS = ["sca", "plab", "casc", "ortho"] as const;

/** The four consumer exams, exported so a selector cannot drift from this list. */
export const EXAM_CODES = EXAMS;

export function normalizeExamCode(value: string | null | undefined): string | null {
  const code = value?.trim().toLowerCase();
  return code && EXAMS.some((exam) => exam === code) ? code : null;
}
export function examAuthHref(path: string, exam: string | null): string {
  const code = normalizeExamCode(exam);
  return code ? `${path}?appType=${encodeURIComponent(code)}` : path;
}

/**
 * The exam every signed-in screen shows: the server's answer (`serverCurrent`, a held exam whenever
 * the person holds one), else the account's own exam. Nothing the browser remembers takes part: a
 * remembered or landing-page exam once outranked the server's answer and sent the marketplace and
 * library to an exam the person did not hold.
 */
export function resolveCurrentExam(input: {
  serverCurrent: string | null;
  accountExam: string | null;
  codes: readonly string[];
}): string | null {
  return input.serverCurrent ?? input.accountExam ?? input.codes[0] ?? null;
}
