/**
 * Who may share a `/me` load, and who must not.
 *
 * Background re-checks (mount, the retry timer, the 401 handler) `join` whatever is in flight:
 * they all ask the same question. A caller that has just changed the stored tokens (a sign-in)
 * asks `after`: a load already in flight started with the old tokens, so its answer (null, or a
 * 401 that signs the person out) is about somebody else. `after` waits for it, then loads again;
 * callers queued behind the same in-flight load share that one follow-up.
 */
export function sessionLoads<T>(load: () => Promise<T>) {
  let inFlight: Promise<T> | null = null;
  let queued: Promise<T> | null = null;

  const start = (): Promise<T> => {
    const current = load().finally(() => {
      if (inFlight === current) inFlight = null;
    });
    inFlight = current;
    return current;
  };

  return {
    join: (): Promise<T> => inFlight ?? start(),
    after: (): Promise<T> => {
      if (!inFlight) return start();
      queued ??= inFlight
        .catch(() => undefined)
        .then(() => {
          queued = null;
          return start();
        });
      return queued;
    },
  };
}
