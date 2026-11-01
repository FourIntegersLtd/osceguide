import type { components } from "@/foundation/platform-client";
import { heldFromDashboard, NO_EXAMS, type HeldExams } from "@/foundation/session/examsAfterLoad";

type Dashboard = components["schemas"]["Dashboard"];

/** How long one answer is shared: long enough to cover one page load's mounts, short enough that a later screen reads fresh. */
const SHARE_FOR_MS = 10_000;

/** What every `useCurrentExam` on the page reads: one answer, one error, one loading flag, for one person. */
interface ExamStoreState {
  userId: string | null;
  held: HeldExams;
  error: Error | null;
  loading: boolean;
}

const INITIAL: ExamStoreState = { userId: null, held: NO_EXAMS, error: null, loading: false };

/**
 * The one `/me/dashboard` read behind every `useCurrentExam` on the page.
 *
 * About 28 screens and nav items mount the hook, often together, so they subscribe to this rather
 * than each asking. `start` joins the request in flight, or reuses an answer less than
 * `shareForMs` old; `reload` always sends a real request (a "Try again" must not be handed the
 * answer it is retrying) and every subscriber sees its loading, answer and error together. A
 * failed request is shared like an answer for the same window (only `reload` retries inside it),
 * so a mount that follows a failure does not restart the load and flip every subscriber to
 * loading. State belongs to one person: a different `userId`, `clear` (sign-out) or the last
 * subscriber leaving drops it, and a response that was superseded by any of those is ignored.
 */
export function createExamStore(
  fetchDashboard: (userId: string) => Promise<Dashboard>,
  { now = Date.now, shareForMs = SHARE_FOR_MS }: { now?: () => number; shareForMs?: number } = {},
) {
  let state: ExamStoreState = INITIAL;
  const listeners = new Set<() => void>();
  let generation = 0;
  let inFlight = false;
  let startedAt: number | null = null;
  let answered = false;

  const set = (next: ExamStoreState) => {
    state = next;
    listeners.forEach((listener) => listener());
  };

  const begin = (base: ExamStoreState, userId: string, showLoading: boolean) => {
    const mine = ++generation;
    inFlight = true;
    startedAt = now();
    set({ ...base, userId, loading: showLoading || base.loading });
    fetchDashboard(userId).then(
      (dashboard) => {
        if (mine !== generation) return;
        inFlight = false;
        answered = true;
        set({ userId, held: heldFromDashboard(dashboard), error: null, loading: false });
      },
      (cause) => {
        if (mine !== generation) return;
        inFlight = false;
        // Kept in `startedAt` like an answer: a mount that follows a failure must not re-ask at once, or a
        // gate that unmounts its screen while `loading` (Capability) would remount it into a request loop.
        // Keep what was known and say so, rather than emptying the exam-filtered navigation.
        set({ ...state, error: cause instanceof Error ? cause : new Error(String(cause)), loading: false });
      },
    );
  };

  const clear = () => {
    if (state === INITIAL) return;
    generation += 1;
    inFlight = false;
    startedAt = null;
    answered = false;
    set(INITIAL);
  };

  return {
    getSnapshot: (): ExamStoreState => state,
    getServerSnapshot: (): ExamStoreState => INITIAL,
    subscribe(listener: () => void): () => void {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
        // Deferred: a route change unmounts the old screen before the new one subscribes.
        if (listeners.size === 0) queueMicrotask(() => listeners.size === 0 && clear());
      };
    },
    /** A signed-in person is on the page: join the load, reuse a fresh answer, or ask. */
    start(userId: string) {
      if (state.userId !== userId) {
        generation += 1;
        answered = false;
        begin({ userId, held: NO_EXAMS, error: null, loading: true }, userId, true);
      } else if (inFlight || (startedAt !== null && now() - startedAt < shareForMs)) {
        return;
      } else {
        begin(state, userId, !answered);
      }
    },
    /** "Try again": a real request, whatever is shared, and every subscriber follows it. */
    reload() {
      if (state.userId === null) return;
      begin(state, state.userId, true);
    },
    /** Signed out (or not yet signed in): nothing of the last person is kept. */
    clear,
  };
}
