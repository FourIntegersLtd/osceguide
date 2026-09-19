"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
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
        setChosen(remembered(userId));
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

  const setCode = useCallback(
    (code: string) => {
      setChosen(code);
      remember(userId, code);
    },
    [userId],
  );

  // A remembered choice only counts while they still hold that exam: access
  // lapses, and the switcher must not keep opening on something now refused.
  const code = useMemo(() => {
    if (chosen && codes.includes(chosen)) return chosen;
    return serverCurrent ?? codes[0] ?? null;
  }, [chosen, codes, serverCurrent]);

  return { codes, code, loading, setCode };
}

const KEY = "osceguide.exam";

/**
 * Keyed by person, because two accounts share one browser more often here than
 * anywhere else — a trainee signing in on a shared machine — and inheriting the
 * previous one's exam would be silent and wrong.
 *
 * Wrapped because `localStorage` itself throws in a private window and in
 * contexts that block site data, not just when it is empty.
 */
function remembered(userId: string): string | null {
  try {
    return window.localStorage.getItem(`${KEY}.${userId}`);
  } catch {
    return null;
  }
}

function remember(userId: string | null, code: string): void {
  if (!userId) return;
  try {
    window.localStorage.setItem(`${KEY}.${userId}`, code);
  } catch {
    // A preference that cannot be stored is not an error worth surfacing; the
    // choice still holds for this page.
  }
}
