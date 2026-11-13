// Per-attempt capture state (next batch number, start time), kept across remounts and reloads:
// the server drops a repeated (attempt_id, seq), and feed offsets must never go negative.

export interface CaptureState {
  nextSeq: number;
  startedAtMs: number;
}

/** The api accepts seq 0..MAX_SEQ; past it we stop posting for that attempt. */
export const MAX_SEQ = 400;

export type KeyValueStorage = Pick<Storage, "getItem" | "setItem">;

const memory = new Map<string, CaptureState>();
const keyFor = (attemptId: string) => `osce_nonverbal_seq:${attemptId}`;

function defaultStorage(): KeyValueStorage | null {
  try {
    return typeof sessionStorage === "undefined" ? null : sessionStorage;
  } catch {
    return null;
  }
}

function valid(value: unknown): value is CaptureState {
  if (typeof value !== "object" || value === null) return false;
  const { nextSeq, startedAtMs } = value as Record<string, unknown>;
  return Number.isInteger(nextSeq) && (nextSeq as number) >= 0 && typeof startedAtMs === "number" && Number.isFinite(startedAtMs);
}

export function loadCaptureState(attemptId: string, storage: KeyValueStorage | null = defaultStorage(), cache = memory): CaptureState | null {
  const cached = cache.get(attemptId);
  if (cached) return cached;
  try {
    const raw = storage?.getItem(keyFor(attemptId));
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (valid(parsed)) {
        cache.set(attemptId, parsed);
        return parsed;
      }
    }
  } catch {
    // Unreadable storage: start fresh.
  }
  return null;
}

export function saveCaptureState(attemptId: string, state: CaptureState, storage: KeyValueStorage | null = defaultStorage(), cache = memory): void {
  cache.set(attemptId, state);
  try {
    storage?.setItem(keyFor(attemptId), JSON.stringify(state));
  } catch {
    // Storage full or blocked: the in-memory copy still serves this page.
  }
}

/** True once the next batch would carry a seq the api refuses. */
export function seqExhausted(nextSeq: number): boolean {
  return nextSeq > MAX_SEQ;
}
