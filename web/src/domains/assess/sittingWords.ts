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


const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const LONG_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** "Thursday 20 November, 09:00"; `fallback` when the date is empty or unreadable. */
export function sittingWhenLong(iso: string | null | undefined, fallback = "Not scheduled"): string {
  const d = iso ? new Date(iso) : null;
  if (!d || Number.isNaN(d.getTime())) return fallback;
  return `${DAYS[d.getDay()]} ${d.getDate()} ${LONG_MONTHS[d.getMonth()]}, ${clock(d)}`;
}

/** "14 October" (no weekday or time); empty when unreadable. */
export function sittingDayLong(iso: string | null | undefined): string {
  const d = iso ? new Date(iso) : null;
  return d && !Number.isNaN(d.getTime()) ? `${d.getDate()} ${LONG_MONTHS[d.getMonth()]}` : "";
}

/** Status chip tone: running is live, a sitting with no circuits warns, scheduled informs. */
export function sittingChipTone(status: string, needsCircuits: boolean): BoardChipTone {
  if (needsCircuits) return "warn";
  if (status === "in_progress") return "live";
  if (status === "scheduled") return "info";
  return "neutral";
}

/** The one inline primary in a sitting's header; everything else sits in the "⋯" menu. */
export type SittingHeadPrimary = "results" | "schedule" | "edit";

export function sittingHeadPrimary(sitting: { status: string; scheduled_for?: string | null }): SittingHeadPrimary {
  if (sitting.status === "completed") return "results";
  if (!sitting.scheduled_for) return "schedule";
  return "edit";
}

/** A rotation's status chip for an employer; the station is not named because an assessor is set per rotation. */
export function rotationChip(circuit: {
  started_at: string | null;
  ended_at: string | null;
  supervisor_user_id: string | null;
  trainee_count: number;
}): { label: string; tone: BoardChipTone } {
  if (circuit.ended_at) return { label: "Finished", tone: "ok" };
  if (circuit.started_at) return { label: "Running", tone: "live" };
  if (!circuit.supervisor_user_id) return { label: "Needs an assessor", tone: "warn" };
  if (circuit.trainee_count > 0) return { label: "Ready", tone: "info" };
  return { label: "Not started", tone: "neutral" };
}

/** "09:00 to 09:55": the sitting's start and the rotation's length from its timing; "" with no date. */
export function rotationTime(
  scheduledFor: string | null,
  stations: number,
  timing: { reading_minutes: number; simulation_minutes: number; break_minutes: number; breaks?: number[]; break_lengths?: { after_station: number; minutes: number }[] },
): string {
  const start = scheduledFor ? new Date(scheduledFor) : null;
  if (!start || Number.isNaN(start.getTime())) return "";
  if (stations === 0) return clock(start);
  const rests = (timing.breaks ?? []).reduce(
    (sum, after) => sum + ((timing.break_lengths ?? []).find((item) => item.after_station === after)?.minutes ?? timing.break_minutes),
    0,
  );
  const minutes = stations * (timing.reading_minutes + timing.simulation_minutes) + rests;
  return `${clock(start)} to ${clock(new Date(start.getTime() + minutes * 60000))}`;
}
