/** What to do with the attempt this tab remembers for a station, by where that attempt now is. */
export type RememberedVerdict = "none" | "reuse" | "resume" | "discard";

/**
 * "none" is for a tab that remembers nothing, decided by the caller. A remembered attempt that was never started is reused when Start is pressed (nothing is
 * created twice). One that is running is offered back as Resume. Anything else (finished,
 * failed, gone or unreadable) is forgotten, so a finished consultation's id is never handed
 * to the next sitting of the station.
 */
export function rememberedVerdict(status: string | null): RememberedVerdict {
  if (status === "created") return "reuse";
  if (status === "running") return "resume";
  return "discard";
}
