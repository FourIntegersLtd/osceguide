const EXAMS = ["sca", "plab", "casc", "ortho"] as const;

export function normalizeExamCode(value: string | null | undefined): string | null {
  const code = value?.trim().toLowerCase();
  return code && EXAMS.some((exam) => exam === code) ? code : null;
}
export function examAuthHref(path: string, exam: string | null): string {
  const code = normalizeExamCode(exam);
  return code ? `${path}?appType=${encodeURIComponent(code)}` : path;
}

/**
 * The exam every signed-in screen shows: the server's answer (`serverCurrent`), which is a held
 * exam whenever the person holds one. Nothing else takes part: not the account's sign-up exam
 * (`users.exam_code`, an unvalidated preference that may name an exam the person does not hold
 * or one that is retired), not anything the browser remembers. `null` is a real answer: the
 * dashboard has not answered, failed, or the server fail-closed on a retired sign-up exam; a
 * screen with no exam asks nothing about one.
 *
 * `codes[0]` covers only a dashboard response that lists exams but names none as current,
 * which the schema allows (`current_exam_code` is optional) though the api does not produce it.
 */
export function resolveCurrentExam(input: { serverCurrent: string | null; codes: readonly string[] }): string | null {
  return input.serverCurrent ?? input.codes[0] ?? null;
}

/** Where a screen stands on "which exam is this person on": see `classifyExam`. */
export type ExamState =
  | { kind: "ready"; code: string }
  | { kind: "loading" }
  | { kind: "unknown"; failed: boolean };

/**
 * Whether a screen that asks the api about an exam may do so yet. Only `ready` carries a code, so
 * no screen can hold `""` (or null) as an exam: `accessState(workspace, "")` is a genuine
 * `hasPaid: false`, and a paying subscriber was shown the free-trial paywall and "0 of 3 free
 * stations" because a null code was coalesced to `""`. With no exam a screen asks nothing, shows
 * no plan or paywall, and says so. Guessing an exam from old sets or the catalogue is how a
 * learner holding one exam got refused on another. `unknown` says whether the dashboard read
 * failed, for copy that differs; `loading` is the one meaning of "waiting on the first answer".
 */
export function classifyExam(input: { code: string | null; loading: boolean; error: Error | null }): ExamState {
  if (input.code) return { kind: "ready", code: input.code };
  if (input.loading) return { kind: "loading" };
  return { kind: "unknown", failed: input.error !== null };
}
