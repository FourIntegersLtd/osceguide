"use client";

import { useMemo } from "react";
import { listExams } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAsync } from "@/foundation/hooks";

export function useAuthoringExamCatalog() {
  const scope = useAuthoringScope();
  const exams = useAsync((signal) => listExams(scope, {}, signal), [scope.base]);

  const items = exams.data?.items ?? [];

  const options = useMemo(
    () =>
      [...items]
        .sort((a, b) => a.code.localeCompare(b.code))
        .map((exam) => ({
          code: exam.code,
          label: `${exam.name} (${exam.code})`,
          rubricVersionId: exam.rubric_version_id ?? null,
        })),
    [items],
  );

  const rubricVersionIdForExam = (examCode: string): string | null => {
    if (!examCode) return null;
    return options.find((row) => row.code === examCode)?.rubricVersionId ?? null;
  };

  return {
    exams: items,
    options,
    loading: exams.loading && !exams.data,
    rubricVersionIdForExam,
  };
}
