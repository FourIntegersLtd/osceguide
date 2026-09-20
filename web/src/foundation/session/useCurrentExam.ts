"use client";

import { useCallback, useEffect, useState } from "react";
import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
import { EXAM_SELECTION_EVENT, readExamSelection, rememberExamSelection, normalizeExamCode } from "./examSelection";
import { useSession } from "@/foundation/session/SessionProvider";

type Dashboard = components["schemas"]["Dashboard"];

export interface CurrentExam {
  /** Every exam this person may open, most-entitled first. */
  codes: string[];
  /** The one every screen is showing. `null` before it resolves, or if they hold none. */
  code: string | null;
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
  const [chosen, setChosen] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status !== "authenticated" || !userId) {
      setCodes([]);
      setChosen(null);
      setServerCurrent(null);
      setLoading(status === "loading");
      return;
    }
    let live = true;
    setLoading(true);
    platformRequest<Dashboard>("/api/v1/me/dashboard")
      .then((data) => {
        if (!live) return;
        setCodes(data.exam_codes ?? []);
        setServerCurrent(data.current_exam_code ?? null);
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

  return { codes, code, loading, setCode };
}
