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
 * The exams `/me/dashboard` describes. A failed request never reaches this: the hook keeps the
 * last answer it held, so the switcher and exam-filtered navigation do not empty on a flaky call.
 */
export function heldFromDashboard(dashboard: Dashboard): HeldExams {
  return {
    codes: dashboard.exam_codes ?? [],
    serverCurrent: dashboard.current_exam_code ?? null,
    dashboardExam: dashboard.current_exam ?? null,
  };
}
