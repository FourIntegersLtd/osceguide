/** * Parse API datetime strings as UTC instants. * Naive ISO strings (no Z or offset) are treated as UTC. matching Python * utcnow().isoformat() semantics and avoiding local-time misinterpretation. */
export function parseApiUtc(iso: string | null | undefined): Date | null {
  if (iso == null || iso === "") return null;
  const s = String(iso).trim();
  if (!s) return null;
  if (/[zZ]$/.test(s) || /[+-]\d{2}:?\d{2}$/.test(s)) {
    return new Date(s);
  }
  if (s.includes("T")) {
    return new Date(`${s}Z`);
  }
  return new Date(s);
} /** Milliseconds since epoch; NaN if invalid. */
export function apiUtcMs(iso: string | null | undefined): number {
  const d = parseApiUtc(iso);
  return d != null && Number.isFinite(d.getTime()) ? d.getTime() : NaN;
} /** Sort comparator for API ISO timestamps (newest first: b - a). */
export function compareApiUtc(
  a: string | null | undefined,
  b: string | null | undefined,
): number {
  return apiUtcMs(a) - apiUtcMs(b);
} /** * Non-null Date for date-fns `format()`, etc. Returns null if invalid. */
export function apiUtcDate(iso: string | null | undefined): Date | null {
  const d = parseApiUtc(iso);
  return d != null && Number.isFinite(d.getTime()) ? d : null;
} /** * Canonical start instant for marketplace posts/sessions: use `scheduled_at` * (UTC) when present; otherwise local wall-clock from date + time (legacy). */
export function marketplaceScheduleStartMs(item: {
  scheduled_at?: string;
  scheduled_date: string;
  scheduled_time: string;
}): number {
  if (item.scheduled_at) {
    const ms = apiUtcMs(item.scheduled_at);
    if (Number.isFinite(ms)) return ms;
  }
  const d = new Date(`${item.scheduled_date}T${item.scheduled_time}:00`);
  return d.getTime();
} /** Display helpers. empty string if unparseable. */
export function formatApiUtcLocaleString(
  iso: string | null | undefined,
  locales?: string | Intl.LocalesArgument,
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = apiUtcDate(iso);
  if (!d) return "";
  return d.toLocaleString(locales as string, options);
}
export function formatApiUtcLocaleDateString(
  iso: string | null | undefined,
  locales?: string | Intl.LocalesArgument,
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = apiUtcDate(iso);
  if (!d) return "";
  return d.toLocaleDateString(locales as string, options);
}
export function formatApiUtcLocaleTimeString(
  iso: string | null | undefined,
  locales?: string | Intl.LocalesArgument,
  options?: Intl.DateTimeFormatOptions,
): string {
  const d = apiUtcDate(iso);
  if (!d) return "";
  return d.toLocaleTimeString(locales as string, options);
}
