const STORAGE_KEY = "osce_live_coverage_hidden";

const listeners = new Set<() => void>();

/**
 * Whether the learner has hidden live marking.
 *
 * On by default: the tick landing mid-consultation is the point of the
 * feature, and nobody discovers a panel that starts switched off.
 *
 * Exposed as an external store so components can read it with
 * `useSyncExternalStore`, which gives the right answer on the server (never
 * hidden) without a hydration mismatch or a setState-in-effect.
 *
 * Reads and writes are guarded: storage is unavailable in some contexts
 * (private windows, blocked site data) and throws rather than returning null.
 */
export function getLiveCoverageHidden(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/** The server has no storage, so nothing is hidden there. */
export function getLiveCoverageHiddenOnServer(): boolean {
  return false;
}

export function subscribeLiveCoverageHidden(onChange: () => void): () => void {
  listeners.add(onChange);
  return () => {
    listeners.delete(onChange);
  };
}

export function setLiveCoverageHidden(hidden: boolean): void {
  try {
    if (hidden) {
      localStorage.setItem(STORAGE_KEY, "1");
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // A preference we cannot persist is not worth failing a consultation over.
  }
  listeners.forEach((listener) => listener());
}
