"use client";

import { useCallback, useEffect, useState } from "react";
import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
import { EXAM_SELECTION_EVENT, readExamSelection, rememberExamSelection, normalizeExamCode } from "./examSelection";
import { useSession } from "@/foundation/session/SessionProvider";

type Dashboard = components["schemas"]["Dashboard"];
type DashboardExam = components["schemas"]["DashboardExam"];
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
  /** Switch exams. Remembered per person, in this browser. */
  setCode: (code: string) => void;
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
 * catalogue. Somebody with one exam never sees a control at all; the switcher
 * for the rare person holding two lives in the navigation, once.
 */
export function useCurrentExam(): CurrentExam {
  const { session, status } = useSession();
  const userId = session?.user.id ?? null;

  const [codes, setCodes] = useState<string[]>([]);
  const [serverCurrent, setServerCurrent] = useState<string | null>(null);
  const [dashboardExam, setDashboardExam] = useState<DashboardExam | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status !== "authenticated" || !userId) {
      setCodes([]);
      setChosen(null);
      setServerCurrent(null);
      setDashboardExam(null);
      setLoading(status === "loading");
      return;
    }
    let live = true;
    setLoading(true);
    loadDashboardOnce(userId)
      .then((data) => {
        if (!live) return;
        setCodes(data.exam_codes ?? []);
        setServerCurrent(data.current_exam_code ?? null);
        setDashboardExam(data.current_exam ?? null);
        setChosen(readExamSelection(userId));
      })
      .catch(() => {
        // An exam nobody can name is better than one invented: every screen
        // below treats `null` as "nothing to show yet" rather than defaulting
        // to SCA, which is how the retiring client marked CASC attempts
        // against a GP rubric.
        if (live) {
          setCodes([]);
          setServerCurrent(null);
          setDashboardExam(null);
        }
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [status, userId]);

  useEffect(() => {
    if (!userId) return;
    const sync = () => setChosen(readExamSelection(userId));
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener(EXAM_SELECTION_EVENT, sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener(EXAM_SELECTION_EVENT, sync);
    };
  }, [userId]);

  const setCode = useCallback(
    (code: string) => {
      setChosen(code);
      if (userId) rememberExamSelection(userId, code);
    },
    [userId],
  );

  // Landing-page selection is navigation context, not an entitlement grant.
  // The API checks access whenever a practice session is started.
  const code = chosen ?? serverCurrent ?? normalizeExamCode(session?.user.exam_code) ?? codes[0] ?? null;

  // The dashboard only ever describes its own `current_exam_code`. Someone
  // who has switched away from it locally (the rare multi-exam holder) sees
  // safe defaults rather than another exam's settings misapplied to this
  // one — the same "nothing invented" rule as the code above.
  const onDashboardExam = dashboardExam !== null && dashboardExam.code === code;
  const name = onDashboardExam ? dashboardExam.name : null;
  const settings = onDashboardExam ? dashboardExam.settings : DEFAULT_EXAM_SETTINGS;

  return { codes, code, name, settings, loading, setCode };
}
