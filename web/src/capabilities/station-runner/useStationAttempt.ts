"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { hasCode } from "@/foundation/platform-client";
import { rememberedVerdict, type RememberedVerdict } from "@/capabilities/station-runner/rememberedAttempt";
import {
  listMyAttempts,
  readAttempt,
  readAttemptBrief,
  readAttemptReview,
  type AttemptBrief,
  type AttemptReview,
} from "@/capabilities/attempt-runner";

export type StationAction = "attempt" | "review";

/** What the person is asked before an attempt exists. */
export type StartGateState = { kind: "start" } | { kind: "resume"; attemptId: string };

export interface StationAttempt {
  /** Set while nothing has been created: press `start` (or `startAgain`) to begin. */
  gate: StartGateState | null;
  /** Begin, picking up this tab's unstarted or running attempt if there is one. */
  start: () => void;
  /** Abandon this tab's running attempt and create a new one. */
  startAgain: () => void;
  attemptId: string | null;
  brief: AttemptBrief | null;
  /** This device's `Date.now()` when the brief arrived: the moment its `server_time` was true. */
  briefReceivedAt: number | null;
  review: AttemptReview | null;
  loading: boolean;
  error: Error | null;
  /**
   * True when this station has been sat as many times as the exam allows.
   *
   * Not an error: the station is still readable, it just cannot be started
   * again. The screen shows it in review rather than a red banner, which is
   * what the retiring client did with its "Completed" pill.
   */
  exhausted: boolean;
  /** Re-read the review once the consultation has finished. */
  reload: () => void;
}

/**
 * The attempt this station screen is showing, and the station behind it.
 *
 * The attempt is created when the person presses Start, not when the screen opens: the reading
 * period reads *its* brief (the library's own read carries no station content on purpose), but
 * an attempt made on open piled up as "Not started" for everyone who only looked.
 *
 * The id is kept in `sessionStorage` under the station being sat. On open it is checked against
 * the server: a running consultation is offered back as Resume, an unstarted one is reused by
 * Start, and a finished or missing one is forgotten, so a stale id is never handed to the next
 * sitting. Session storage rather than local: it belongs to this tab's sitting of this
 * station, and a second tab is a second attempt, which is the truth.
 */
export function useStationAttempt({
  key,
  action,
  create,
  attemptIdFromUrl,
  stationVersionId,
  setEntryId,
}: {
  /** Identifies the station being sat, for the remembered attempt. */
  key: string;
  action: StationAction;
  /** How this station starts an attempt. Only called in `attempt` mode. */
  create: () => Promise<{ id: string }>;
  /** An explicit attempt to review, from the query string. */
  attemptIdFromUrl?: string | null;
  stationVersionId?: string | null;
  setEntryId?: string | null;
}): StationAttempt {
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [brief, setBrief] = useState<AttemptBrief | null>(null);
  const [briefReceivedAt, setBriefReceivedAt] = useState<number | null>(null);
  const [review, setReview] = useState<AttemptReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [exhausted, setExhausted] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [gate, setGate] = useState<StartGateState | null>(null);
  /** Set once Start is pressed; `fresh` abandons the remembered attempt. */
  const [go, setGo] = useState<{ fresh: boolean } | null>(null);
  /*
   * One creation per station, however many times the effect runs.
   *
   * React re-invokes effects in development, and the `sessionStorage` guard
   * cannot catch that: both runs read an empty key before either writes one,
   * so two attempts were created and the exam's limit lost a go on every page
   * load. Found by opening the station in a browser — the attempt listing had
   * two `created` rows for one visit.
   */
  const creating = useRef<Promise<{ id: string }> | null>(null);
  const createdFor = useRef<string | null>(null);

  const reload = useCallback(() => setReloadKey((n) => n + 1), []);
  const start = useCallback(() => setGo({ fresh: false }), []);
  const startAgain = useCallback(() => {
    forgetStationAttempt(key);
    createdFor.current = null;
    creating.current = null;
    setGo({ fresh: true });
  }, [key]);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    setExhausted(false);

    void (async () => {
      try {
        let id: string | null;
        let reviewing = action === "review";

        if (reviewing) {
          id = attemptIdFromUrl ?? (await latestFinished({ stationVersionId, setEntryId }));
        } else {
          const found = await resolveRemembered(key);
          id = found.id;
          if (!go) {
            if (!live) return;
            setGate(found.verdict === "resume" && id ? { kind: "resume", attemptId: id } : { kind: "start" });
            setAttemptId(null);
            return;
          }
          setGate(null);
          if (!id) {
            if (createdFor.current !== key) {
              createdFor.current = key;
              creating.current = create();
            }
            try {
              id = (await creating.current!).id;
            } catch (cause) {
              // Forget the failed creation, or "Try again" would await the same rejection.
              createdFor.current = null;
              creating.current = null;
              // Out of goes. The station is still theirs to read back, so this
              // falls through to the review rather than refusing the screen.
              if (!hasCode(cause, "attempt_limit_reached", "set_locked")) throw cause;
              if (live) setExhausted(true);
              reviewing = true;
              id = await latestFinished({ stationVersionId, setEntryId });
            }
          }
        }

        if (!live) return;
        if (!id) {
          // Review mode with nothing sat yet. Not an error: the tabs show
          // their own empty states.
          setAttemptId(null);
          setBrief(null);
          setReview(null);
          return;
        }

        if (!reviewing) remember(key, id);
        setAttemptId(id);

        const [briefResult, reviewResult] = await Promise.all([
          readAttemptBrief(id),
          reviewing
            ? readAttemptReview(id).catch((cause) => {
                // Still being marked, or the candidate walked out before the
                // consultation. Neither is an error worth a red banner.
                if (hasCode(cause, "attempt_not_finished")) return null;
                throw cause;
              })
            : Promise.resolve(null),
        ]);
        if (!live) return;
        setBrief(briefResult);
        setBriefReceivedAt(Date.now());
        setReview(reviewResult);
      } catch (cause) {
        if (live) setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        if (live) setLoading(false);
      }
    })();

    return () => {
      live = false;
    };
    // `create` is a new closure every render in most callers; the station key
    // is what actually identifies the work.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, action, attemptIdFromUrl, stationVersionId, setEntryId, reloadKey, go]);

  return { attemptId, brief, briefReceivedAt, review, loading, error, exhausted, reload, gate, start, startAgain };
}

/**
 * The most recent **finished** attempt at this station.
 *
 * Not simply the most recent: opening a station creates one, so the newest is
 * usually the one being sat right now, and reviewing it answers
 * `attempt_not_finished` and shows an empty management tab. Found in a
 * browser, where clicking from the consultation into Management showed
 * nothing at all.
 *
 * Falls back to the newest of any kind so that a station with only an
 * in-progress attempt still names one, rather than the screen claiming
 * nothing has ever been sat.
 */
async function latestFinished(params: {
  stationVersionId?: string | null;
  setEntryId?: string | null;
}): Promise<string | null> {
  const page = await listMyAttempts({ ...params, limit: 25 });
  const consultations = page.items.filter((item) => item.kind !== "debrief");
  const finished = consultations.find((item) => FINISHED.has(item.status));
  return finished?.id ?? consultations[0]?.id ?? null;
}

/**
 * The attempt this tab remembers for the station and what to do with it, or no id when it
 * remembers none or the one it remembered is discarded. A discarded one is forgotten here, so it is never handed to the next sitting.
 */
async function resolveRemembered(key: string): Promise<{ id: string | null; verdict: RememberedVerdict }> {
  const id = remembered(key);
  if (!id) return { id: null, verdict: "none" };
  const status = await readAttempt(id).then(
    (found) => found.status,
    () => null,
  );
  const verdict = rememberedVerdict(status);
  if (verdict === "discard") {
    forgetStationAttempt(key);
    return { id: null, verdict };
  }
  return { id, verdict };
}

/** An attempt with something to review: the consultation is over, either way. */
const FINISHED = new Set(["interaction_complete", "evaluated", "failed"]);

const KEY = "osceguide.station-attempt";

function remembered(key: string): string | null {
  try {
    return window.sessionStorage.getItem(`${KEY}.${key}`);
  } catch {
    return null;
  }
}

function remember(key: string, attemptId: string): void {
  try {
    window.sessionStorage.setItem(`${KEY}.${key}`, attemptId);
  } catch {
    // Storage is blocked. A reload will start a second attempt, which is worse
    // than this but not worth refusing to run the station over.
  }
}

/** Forget the remembered attempt, once it has been finished. */
export function forgetStationAttempt(key: string): void {
  try {
    window.sessionStorage.removeItem(`${KEY}.${key}`);
  } catch {
    // Nothing to do; a stale key only costs a reused id on a finished attempt,
    // which the backend refuses anyway.
  }
}
