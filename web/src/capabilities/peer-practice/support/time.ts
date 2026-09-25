/**
 * The words this capability puts on a clock.
 *
 * The retiring screens carried a calendar date and a wall-clock time as two
 * strings and re-derived a timestamp from them in six places, each with its own
 * padding and its own idea of what "today" meant. `platform-api` serves one
 * `starts_at` instant, so everything below is a rendering of that instant in
 * the reader's own zone — which is also the bug fix: a slot offered at 19:00 in
 * London no longer reads as 19:00 to somebody in Lagos.
 */

/** The session opens this long before its appointed hour — `marketplace/domain.py`. */
export const JOIN_OPENS_MINUTES = 20;

/** How long a claimed session stays joinable after its start. */
export const JOIN_WINDOW_HOURS = 1;

export function startMs(startsAt: string): number {
  return new Date(startsAt).getTime();
}

export function isPast(startsAt: string, now = Date.now()): boolean {
  return startMs(startsAt) < now;
}

/** "Today", else "Sat, 3 May". The card's compact form. */
export function shortDate(startsAt: string, now = new Date()): string {
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) return "";
  const sameDay =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear();
  if (sameDay) return "Today";
  return date.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

/** "Saturday, 3 May". The confirmation and the upcoming card. */
export function longDate(startsAt: string): string {
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

/** "14:30". Twenty-four hour, as the card has always shown it. */
export function clockTime(startsAt: string): string {
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) return "";
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

/** "2:30 PM". The wordier form the modals use. */
export function meridiemTime(startsAt: string): string {
  const date = new Date(startsAt);
  if (Number.isNaN(date.getTime())) return "";
  const hours = date.getHours();
  const suffix = hours >= 12 ? "PM" : "AM";
  return `${hours % 12 || 12}:${String(date.getMinutes()).padStart(2, "0")} ${suffix}`;
}

/** "2h 5m", or "45 min" under the hour. Null once the session may be joined. */
export function timeUntilJoin(startsAt: string, now = Date.now()): string | null {
  const minutes = Math.floor((startMs(startsAt) - now) / 60_000);
  if (minutes <= JOIN_OPENS_MINUTES) return null;
  const hours = Math.floor(minutes / 60);
  return hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes} min`;
}

export function canJoin(startsAt: string, now = Date.now()): boolean {
  return startMs(startsAt) - now <= JOIN_OPENS_MINUTES * 60_000;
}

/** Past the window in which anybody is still going to turn up. */
export function joinWindowClosed(startsAt: string, now = Date.now()): boolean {
  return now - startMs(startsAt) > JOIN_WINDOW_HOURS * 3_600_000;
}

/** "7:03" — a running clock, not a date. */
export function formatElapsed(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`;
}

/** The `datetime-local` value a form field wants, in the reader's own zone. */
export function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** A calendar day and an `HH:mm` back into the instant the API stores. */
export function toInstant(day: string, time: string): string {
  const [hours = "00", minutes = "00"] = time.split(":");
  return new Date(`${day}T${hours.padStart(2, "0")}:${minutes}:00`).toISOString();
}

export function isScheduleInPast(day: string, time: string, now = Date.now()): boolean {
  const ms = new Date(toInstant(day, time)).getTime();
  return !Number.isFinite(ms) || ms <= now;
}
