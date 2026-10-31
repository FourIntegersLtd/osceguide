"use client";

import { useMemo } from "react";
import { useCurrentExam } from "@/foundation/session";
import type { Dashboard } from "@/domains/train/api";

export interface DashboardExam {
  code: string;
  attempts: number;
}

/**
 * How much this person has done in the exam the app is showing.
 *
 * This used to decide *which* exam as well, from what had been attempted,
 * granted or built a practice set for — and it offered a picker in the header
 * when there was more than one. Three other screens each made a different
 * decision the same way. There is one answer now (`useCurrentExam`, from the
 * backend) and no switcher.
 */
export function useDashboardExam(data: Dashboard): {
  examCode: string;
  attempts: number;
} {
  const { code } = useCurrentExam();
  const exams = useMemo(() => availableExams(data), [data]);
  const examCode = code ?? exams[0]?.code ?? "sca";
  const attempts = exams.find((exam) => exam.code === examCode)?.attempts ?? 0;
  return { examCode, attempts };
}


/**
 * How many attempts this person has in each exam.
 *
 * Only ever read for the exam being shown now, but built as a map because the
 * dashboard payload reports progress per exam and picking one row out of it is
 * the same walk.
 */
function availableExams(data: Dashboard): DashboardExam[] {
  const counts = new Map<string, number>();

  for (const exam of data.progress ?? []) {
    counts.set(exam.exam_code, exam.attempts ?? 0);
  }
  /*
   * Live entitlements only. `list_for_user` returns revoked and expired rows
   * too, and an exam somebody no longer has access to is not one to open the
   * dashboard on.
   */
  for (const entitlement of data.entitlements ?? []) {
    if (!entitlement.live) continue;
    if (!counts.has(entitlement.exam_code)) counts.set(entitlement.exam_code, 0);
  }
  for (const set of data.sets ?? []) {
    if (!counts.has(set.exam_code)) counts.set(set.exam_code, 0);
  }

  return [...counts.entries()]
    .map(([code, attempts]) => ({ code, attempts }))
    .sort((a, b) => b.attempts - a.attempts || a.code.localeCompare(b.code));
}
