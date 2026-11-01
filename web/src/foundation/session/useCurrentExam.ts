"use client";

import { useEffect, useSyncExternalStore } from "react";
import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
import { resolveCurrentExam } from "./examCode";
import { NO_EXAMS } from "@/foundation/session/examsAfterLoad";
import { createExamStore } from "@/foundation/session/examStore";
import { useSession } from "@/foundation/session/SessionProvider";

type Dashboard = components["schemas"]["Dashboard"];
export type ExamSettings = components["schemas"]["ExamSettings"];

/**
 * What every screen gets before the dashboard answers, and for any exam the
 * dashboard did not describe. Matches the backend's own field defaults
 * (`app/core/exam_settings.py`), so a screen reading this before the real
 * settings land behaves exactly as an exam with `{}` stored would.
 */
const DEFAULT_EXAM_SETTINGS: ExamSettings = {
  date_label: "Exam date",
  help_modes: ["navigate"],
  peer_waiting_email: false,
  session_modes: ["debrief", "practice_as_patient"],
  show_tips_while_marking: false,
  station_subtypes: [],
};

// The api names the person from the session token; the user id only scopes the shared answer.
const examStore = createExamStore(() => platformRequest<Dashboard>("/api/v1/me/dashboard"));

export interface CurrentExam {
  /** Every exam this person may open, most-entitled first. */
  codes: string[];
  /** The one every screen is showing. `null` before it resolves, or if they hold none. */
  code: string | null;
  /** That exam's display name, from the backend. `null` until it resolves. */
  name: string | null;
  /**
   * Everything that differs between exams apart from the rubric — date label,
   * session modes, station sub-types, help modes and the rest
   * (`app/core/exam_settings.py`). Always a whole object, defaulted to match
   * an exam stored as `{}`, so a screen never has to null-check it while the
   * dashboard is still loading.
   */
  settings: ExamSettings;
  /** True while it is still being fetched, so a screen can wait rather than guess. */
  loading: boolean;
  /** Why the dashboard could not be read, if it could not. The last known exams are still returned. */
  error: Error | null;
  /** Ask the dashboard again. */
  reload: () => void;
}

/**
 * Which exam the whole signed-in app is showing: the one the backend names, and only that one.
 *
 * `exam_codes` and `current_exam_code` on `GET /me/dashboard` are live entitlements plus the
 * exam the account was opened for, filtered through the published catalogue, and `current` is a
 * held exam whenever the person holds one. Nobody picks an exam in the browser and nothing is
 * remembered there; moving someone to another exam is a support action. While the dashboard has
 * not answered (or failed, or named none) `code` is `null`, and a screen asks nothing about an
 * exam: it must not fall back to the account's sign-up exam, which the person may not hold.
 */
export function useCurrentExam(): CurrentExam {
  const { session, status } = useSession();
  const userId = session?.user.id ?? null;

  const snapshot = useSyncExternalStore(examStore.subscribe, examStore.getSnapshot, examStore.getServerSnapshot);

  useEffect(() => {
    if (status === "authenticated" && userId) examStore.start(userId);
    else examStore.clear();
  }, [status, userId]);

  // Another person's answer (or none yet) is never shown: until the store is on this user, wait.
  const mine = userId !== null && snapshot.userId === userId;
  const { codes, serverCurrent, dashboardExam } = mine ? snapshot.held : NO_EXAMS;
  const error = mine ? snapshot.error : null;
  const loading = status === "loading" || (userId !== null && (!mine || snapshot.loading));
  const reload = examStore.reload;

  const code = resolveCurrentExam({ serverCurrent, codes });

  // The dashboard only describes its own `current_exam_code`; any other code (there is none
  // today) sees safe defaults, never another exam's settings misapplied to it.
  const onDashboardExam = dashboardExam !== null && dashboardExam.code === code;
  const name = onDashboardExam ? dashboardExam.name : null;
  const settings = onDashboardExam ? dashboardExam.settings : DEFAULT_EXAM_SETTINGS;

  return { codes, code, name, settings, loading, error, reload };
}
