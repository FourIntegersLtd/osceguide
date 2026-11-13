// Which face the cues panel shows, and the wording of each feed row. Pure.
import type { NonverbalLingo } from "./api";
import type { CueKind } from "./cues";
import type { CaptureStatus } from "./useNonverbalCapture";

export type PanelKind = "hidden" | "invite" | "denied" | "unavailable" | "ready" | "live";

/** The panel's state from the read, the candidate's switch, the room phase and the camera status. */
export function panelKind(input: {
  supported: boolean;
  consented: boolean;
  off: boolean;
  isLive: boolean;
  status: CaptureStatus;
}): PanelKind {
  if (!input.supported) return "hidden";
  if (!input.consented || input.off) return "invite";
  if (input.status === "denied") return "denied";
  if (input.status === "unavailable") return "unavailable";
  return input.isLive ? "live" : "ready";
}

/** The exam's own label a cue sits under (attention, listening or rapport). */
export function cueLabel(kind: CueKind, lingo: NonverbalLingo): string {
  switch (kind) {
    case "nod":
      return lingo.listening_label;
    case "smile":
      return lingo.rapport_label;
    case "attention":
      return lingo.attention_label;
  }
}

/** `m:ss` into the consultation for a feed row. */
export function feedRowTime(atMs: number, startedAtMs: number): string {
  const seconds = Math.max(0, Math.floor((atMs - startedAtMs) / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
