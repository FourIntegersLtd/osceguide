import type { ToastTone } from "./ToastContext";

export const DEFAULT_DURATION_MS = 4500;
export const ERROR_DURATION_MS = 8000;
/** The longest a toast may stay: nothing sits on screen for ever. */
export const MAX_DURATION_MS = 60_000;

/** How long a toast stays, in ms: its own `durationMs` (capped at 60 s), else 8 s for an error, else 4.5 s. */
export function toastDurationMs(
  input: { durationMs?: number },
  tone: ToastTone,
): number {
  if (input.durationMs) return Math.min(input.durationMs, MAX_DURATION_MS);
  return tone === "error" ? ERROR_DURATION_MS : DEFAULT_DURATION_MS;
}
