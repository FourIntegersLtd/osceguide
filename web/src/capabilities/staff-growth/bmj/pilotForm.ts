import type { PilotConfigUpdate } from "@/capabilities/staff-growth/api";

/** Pounds typed as "500, 1000" become whole pence; anything unreadable is dropped. */
export function parseThresholdsInput(value: string): number[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => Math.round(Number.parseFloat(part) * 100))
    .filter((pence) => Number.isFinite(pence));
}

/** Whole pounds, joined for the text field ("500, 1000"). */
export function formatThresholdsForInput(thresholds: readonly number[]): string {
  return thresholds.map((pence) => (pence / 100).toFixed(0)).join(", ");
}

/** The rate field, in pounds. */
export function formatRateForInput(pence: number): string {
  return (pence / 100).toFixed(2);
}

/** Thresholds as a comparable string, whatever order they were typed in. */
function sorted(thresholds: readonly number[]): string {
  return [...thresholds].sort((a, b) => a - b).join();
}

/**
 * The PATCH body for the pilot form, or null when the rate is not a valid amount.
 * Alert history is forgotten only when the thresholds changed: a rate-only edit
 * must not make already-sent alerts fire again.
 */
export function pilotUpdateFromForm(
  ratePounds: string,
  thresholdsInput: string,
  currentThresholds: readonly number[],
): PilotConfigUpdate | null {
  const pence = Math.round(Number.parseFloat(ratePounds) * 100);
  if (!Number.isFinite(pence) || pence < 0) return null;
  const thresholds = parseThresholdsInput(thresholdsInput);
  return {
    cost_per_click_pence: pence,
    spend_alert_thresholds_pence: thresholds,
    reset_spend_alerts: sorted(thresholds) !== sorted(currentThresholds),
  };
}
