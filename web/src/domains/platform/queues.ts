import { parseApiDate, plural } from "@/foundation/format";

/** "No open reports", "1 open report", "3 open reports". */
export function openReportsHeadline(open: number): string {
  return open === 0 ? "No open reports" : `${plural(open, "open report")}`;
}

/** "The oldest has waited 3 days": whole days, or hours under a day. */
export function oldestWaitedLine(createdAt: string | null | undefined, now: Date = new Date()): string | null {
  const created = parseApiDate(createdAt);
  if (!created) return null;
  const hours = Math.max(0, Math.floor((now.getTime() - created.getTime()) / 3_600_000));
  if (hours < 1) return "The oldest has waited under an hour";
  if (hours < 24) return `The oldest has waited ${plural(hours, "hour")}`;
  return `The oldest has waited ${plural(Math.floor(hours / 24), "day")}`;
}

/** "3 waiting"; a full page means there may be more behind it. */
export function waitingHeadline(count: number, hasMore: boolean): string {
  if (count === 0) return "Nothing waiting";
  return hasMore ? `More than ${count} waiting` : `${count} waiting`;
}

/** A reply lands in an inbox only if the sender had an account. */
export function canReplyInApp(message: { user_id?: string | null }): boolean {
  return Boolean(message.user_id);
}

/** "mailto:" for a sender who wrote without signing in; null when they left no address. */
export function mailtoFor(message: { email?: string | null; subject?: string | null }): string | null {
  if (!message.email) return null;
  const subject = message.subject ? `?subject=${encodeURIComponent(`Re: ${message.subject}`)}` : "";
  return `mailto:${message.email}${subject}`;
}
