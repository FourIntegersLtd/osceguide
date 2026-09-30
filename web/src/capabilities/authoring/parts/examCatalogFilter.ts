/** Client-side exam scoping until list endpoints accept `exam_code`. */

export const AUTHORING_ALL_EXAMS = "";

export function normalizeExamCode(code: string): string {
  return code.trim().toLowerCase();
}

export function matchesExamFilter(
  itemCode: string | null | undefined,
  selectedExam: string,
  options: { includeUnscoped?: boolean } = {},
): boolean {
  if (!selectedExam) return true;
  const want = normalizeExamCode(selectedExam);
  if (!itemCode || itemCode.trim() === "") {
    return options.includeUnscoped === true;
  }
  return normalizeExamCode(itemCode) === want;
}
