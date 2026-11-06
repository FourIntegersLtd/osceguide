import type { BoardChipTone } from "@/foundation/ui/boardKit";
/** The date words and status tone the sitting boards print. Pure, so a node test covers it (no tsx imports). */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const two = (n: number) => String(n).padStart(2, "0");
const sameDay = (a: Date, b: Date) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
const dayMonth = (d: Date, now: Date) => `${d.getDate()} ${MONTHS[d.getMonth()]}${d.getFullYear() === now.getFullYear() ? "" : ` ${d.getFullYear()}`}`;
const clock = (d: Date) => `${two(d.getHours())}:${two(d.getMinutes())}`;

/** "Today 09:00" for today, else "12 Nov" (with the year when it is not this one). Empty or unreadable: "Not scheduled". */
export function sittingWhen(iso: string | null | undefined, now: Date = new Date()): string {
  const d = iso ? new Date(iso) : null;
  if (!d || Number.isNaN(d.getTime())) return "Not scheduled";
  return sameDay(d, now) ? `Today ${clock(d)}` : dayMonth(d, now);
}

/** The same with the time on every day: "Today 09:00", "12 Mar, 09:00". */
export function sittingWhenAt(iso: string | null | undefined, now: Date = new Date()): string {
  const d = iso ? new Date(iso) : null;
  if (!d || Number.isNaN(d.getTime())) return "Not scheduled";
  return sameDay(d, now) ? `Today ${clock(d)}` : `${dayMonth(d, now)}, ${clock(d)}`;
}


/** Status chip tone: running is live, a sitting with no circuits warns, scheduled informs. */
export function sittingChipTone(status: string, needsCircuits: boolean): BoardChipTone {
  if (needsCircuits) return "warn";
  if (status === "in_progress") return "live";
  if (status === "scheduled") return "info";
  return "neutral";
}
