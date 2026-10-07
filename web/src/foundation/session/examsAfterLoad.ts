import type { components } from "@/foundation/platform-client";

type Dashboard = components["schemas"]["Dashboard"];
type DashboardExam = components["schemas"]["DashboardExam"];

/** What the dashboard says about the person's exams. */
export interface HeldExams {
  codes: string[];
  serverCurrent: string | null;
  dashboardExam: DashboardExam | null;
}

export const NO_EXAMS: HeldExams = { codes: [], serverCurrent: null, dashboardExam: null };

/**
 * The exams to show once `/me/dashboard` has answered, or failed.
 *
 * A failure keeps what was last known: the switcher and the exam-filtered navigation are built
 * from these, and emptying them on a flaky request made them vanish until a reload. An exam
 * nobody can name is still never invented: with nothing known before, nothing is shown.
 */
export function examsAfterLoad(previous: HeldExams, outcome: { dashboard: Dashboard } | { failed: true }): HeldExams {
  if ("failed" in outcome) return previous;
  const { dashboard } = outcome;
  return {
    codes: dashboard.exam_codes ?? [],
    serverCurrent: dashboard.current_exam_code ?? null,
    dashboardExam: dashboard.current_exam ?? null,
  };
}
