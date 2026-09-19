"use client";

import { useAsync, type AsyncState } from "@/foundation/hooks";
import { listExams, type Exam } from "@/capabilities/stations";

/**
 * One exam by code, with its timings.
 *
 * Reading and simulation lengths come from the exam rather than from constants
 * in the browser. The old clients each had their own clamping helper, so the
 * same station ran for different lengths depending on which one you opened it
 * in.
 */
export function useExam(examCode: string | null | undefined): AsyncState<Exam | null> {
  return useAsync(
    async (signal) => {
      if (!examCode) return null;
      const page = await listExams(signal);
      return page.items.find((exam) => exam.code === examCode) ?? null;
    },
    [examCode],
  );
}
