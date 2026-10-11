import type { ToastTone } from "./ToastContext";

export const DEFAULT_DURATION_MS = 4500;
export const ERROR_DURATION_MS = 8000;
/** Even a `persistent` toast goes after a minute: nothing sits on screen for ever. */
export const PERSISTENT_CAP_MS = 60_000;

/** How long a toast stays, in ms. Always finite. */
export function toastDurationMs(
  input: { persistent?: boolean; durationMs?: number },
  tone: ToastTone,
): number {
  if (input.persistent) return PERSISTENT_CAP_MS;
  if (input.durationMs) return input.durationMs;
  return tone === "error" ? ERROR_DURATION_MS : DEFAULT_DURATION_MS;
}
