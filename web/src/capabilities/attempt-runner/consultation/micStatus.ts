/** What the candidate is told about their microphone, worst news first. */
export function micStatus({
  blocked,
  connected,
  enabled,
  speaking,
  level,
}: {
  blocked: boolean;
  connected: boolean;
  enabled: boolean;
  speaking: boolean;
  /** 0 to 1, from LiveKit's `audioLevel`. */
  level: number;
}): string {
  if (blocked) return "Mic blocked";
  if (!connected) return "Preparing mic…";
  if (!enabled) return "Mic off";
  if (!speaking) return "Mic ready";
  if (level < 0.05) return "Speak up a little";
  return level < 0.9 ? "Mic hears you" : "Very loud";
}
