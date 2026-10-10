/** Pure helpers for the inbox screen and the shell's unread badge. */

/** The pill text: the number, capped so it never outgrows the rail. */
export function unreadLabel(count: number): string {
  return count > 9 ? "9+" : String(count);
}

/** "3 unread messages", "1 unread message", or the all-clear. */
export function heroHeadline(unread: number): string {
  if (unread <= 0) return "You're up to date";
  return `${unread} unread ${unread === 1 ? "message" : "messages"}`;
}

/** What kind of message it is, for the row's meta line. */
export function kindLabel(kind: string): string {
  switch (kind) {
    case "announcement":
      return "Announcement";
    case "report_answer":
      return "Answer to your report";
    case "reply":
      return "Reply";
    default:
      return "Message";
  }
}
