import { useAsync } from "@/foundation/hooks";
import { listAllProgrammes, listExams, type Exam, type Programme } from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import { programmeFor } from "@/capabilities/authoring/sections/examSteps";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";

export type ExamWithProgramme = { exam: Exam; programme: Programme | null };

/** One exam and its programme, or null when there is no such exam (deleted, or not this organisation's). */
export async function loadExam(
  scope: AuthoringScope,
  examId: string,
  signal?: AbortSignal,
): Promise<ExamWithProgramme | null> {
  const exams = await listExams(scope, { status: "all" }, signal);
  const exam = exams.items.find((item) => item.id === examId) ?? null;
  if (!exam) return null;
  return { exam, programme: programmeFor(await listAllProgrammes(scope, signal), exam) };
}

export function useExam(examId: string | null) {
  const scope = useAuthoringScope();
  return useAsync(
    async (signal) => (examId ? loadExam(scope, examId, signal) : null),
    [scope.base, examId],
  );
}
