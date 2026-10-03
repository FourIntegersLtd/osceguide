/** The longest timer the settings accept: the old modal's 60 minutes and 59 seconds. */
const MAX_SECONDS = 60 * 60 + 59;

/** Seconds as the field shows them: 240 reads "04:00". */
export function formatTimer(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/**
 * What somebody typed into a timer field, in seconds.
 *
 * "14:00" and a bare "14" both mean fourteen minutes. Anything else, a zero,
 * or more than an hour is `null`, which the form reports instead of saving.
 */
export function parseTimer(value: string): number | null {
  const match = /^(\d{1,2})(?::([0-5]\d))?$/.exec(value.trim());
  if (!match) return null;
  const total = Number(match[1]) * 60 + Number(match[2] ?? 0);
  return total >= 1 && total <= MAX_SECONDS ? total : null;
}

/** "4 min" or "4 min 30 s", for the sentence that says which timers apply. */
export function describeTimer(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return seconds === 0 ? `${minutes} min` : `${minutes} min ${seconds} s`;
}
