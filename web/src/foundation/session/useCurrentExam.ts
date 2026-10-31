"use client";

import { useCallback, useEffect, useState } from "react";
import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
import { normalizeExamCode, resolveCurrentExam } from "./examSelection";
import { heldFromDashboard, NO_EXAMS, type HeldExams } from "@/foundation/session/examsAfterLoad";
import { useSession } from "@/foundation/session/SessionProvider";

type Dashboard = components["schemas"]["Dashboard"];
export type ExamSettings = components["schemas"]["ExamSettings"];

/**
 * What every screen gets before the dashboard answers, and what an exam this
 * hook cannot describe (a `chosen` override the dashboard never priced in)
 * falls back to. Matches the backend's own field defaults
 * (`app/core/exam_settings.py`), so a screen reading this before the real
 * settings land behaves exactly as an exam with `{}` stored would.
 */
export const DEFAULT_EXAM_SETTINGS: ExamSettings = {
  date_label: "Exam date",
  help_modes: ["navigate"],
  peer_waiting_email: false,
  session_modes: ["debrief", "practice_as_patient"],
  show_tips_while_marking: false,
  station_subtypes: [],
};

/** How long one answer is shared: long enough to cover one page load's mounts, short enough that a later screen reads fresh. */
const SHARE_FOR_MS = 10_000;

/** The one `/me/dashboard` request every caller on the page is waiting on, per person. */
let sharedLoad: { userId: string; startedAt: number; request: Promise<Dashboard> } | null = null;

/**
 * Ask for `/me/dashboard` once for everybody mounting at the same time.
 *
 * About 28 screens and nav items use this hook. Without sharing, one dashboard
 * load would send about a dozen identical requests. A
 * failed request is not shared, so the next caller asks again.
 */
function loadDashboardOnce(userId: string): Promise<Dashboard> {
  const now = Date.now();
  if (sharedLoad && sharedLoad.userId === userId && now - sharedLoad.startedAt < SHARE_FOR_MS) {
    return sharedLoad.request;
  }
  const request = platformRequest<Dashboard>("/api/v1/me/dashboard");
  const thisLoad = { userId, startedAt: now, request };
  sharedLoad = thisLoad;
  request.catch(() => {
    if (sharedLoad === thisLoad) sharedLoad = null;
  });
  return request;
}

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
 * Which exam the whole signed-in app is showing.
 *
 * The retiring client answered this with a hostname: `sca.osceguide.com` set an
 * `appType` that every request carried, so there was one exam for the session
 * and the product had no exam picker anywhere. On one domain that had to be
 * derived, and four screens each derived it differently — the dashboard from
 * what had been attempted, the station library from the whole published
 * catalogue, peer practice from whichever exam sorted first. The result was a
 * dropdown on four screens of a product where holding one exam is the norm,
 * over exams nobody had bought.
 *
 * There is one answer now and the backend gives it: `exam_codes` and
 * `current_exam_code` on `GET /me/dashboard`, which are live entitlements plus
 * the exam the account was opened for, filtered through the published
 * catalogue. Nobody picks an exam: there is no switcher, the app
 * shows the one the backend names.
 */
export function useCurrentExam(): CurrentExam {
  const { session, status } = useSession();
  const userId = session?.user.id ?? null;

  const [held, setHeld] = useState<HeldExams>(NO_EXAMS);
  const { codes, serverCurrent, dashboardExam } = held;
  const [error, setError] = useState<Error | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((n) => n + 1), []);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status !== "authenticated" || !userId) {
      setHeld(NO_EXAMS);
      setError(null);
      setLoading(status === "loading");
      return;
    }
    let live = true;
    setLoading(true);
    loadDashboardOnce(userId)
      .then((dashboard) => {
        if (!live) return;
        setHeld(heldFromDashboard(dashboard));
        setError(null);
      })
      .catch((cause) => {
        // Keep what was known and say so, rather than emptying the
        // exam-filtered navigation.
        if (!live) return;
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [status, userId, reloadKey]);

  const code = resolveCurrentExam({
    serverCurrent,
    accountExam: normalizeExamCode(session?.user.exam_code),
    codes,
  });

  // The dashboard only ever describes its own `current_exam_code`. When
  // the code is anything else (the account's own exam, before the dashboard answers) it
  // sees safe defaults rather than another exam's settings misapplied to this one — the same "nothing invented" rule as the code above.
  const onDashboardExam = dashboardExam !== null && dashboardExam.code === code;
  const name = onDashboardExam ? dashboardExam.name : null;
  const settings = onDashboardExam ? dashboardExam.settings : DEFAULT_EXAM_SETTINGS;

  return { codes, code, name, settings, loading, error, reload };
}
