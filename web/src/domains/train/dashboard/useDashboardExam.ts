"use client";

import { useMemo, useState } from "react";
import type { Dashboard } from "@/domains/train/api";

export interface DashboardExam {
  code: string;
  attempts: number;
}

/**
 * Which exam the dashboard is showing, and which it could show.
 *
 * The retiring client answered this with a subdomain: `sca.osceguide.com`
 * carried an `appType` through a context, and each exam had its own build of
 * the same screen. The platform has one workspace and one dashboard, and the
 * person may hold access to more than one exam — so the exams come from what
 * they have actually attempted or been granted, most-practised first, and the
 * picker in the header switches between them.
 *
 * A person with one exam never sees the control.
 */
export function useDashboardExam(data: Dashboard): {
  exams: DashboardExam[];
  examCode: string;
  setExamCode: (code: string) => void;
  attempts: number;
} {
  const exams = useMemo(() => availableExams(data), [data]);
  const [selected, setSelected] = useState<string | null>(null);

  const examCode = selected && exams.some((exam) => exam.code === selected)
    ? selected
    : (exams[0]?.code ?? "sca");

  const attempts = exams.find((exam) => exam.code === examCode)?.attempts ?? 0;

  return { exams, examCode, setExamCode: setSelected, attempts };
}

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
