// Live cue wording from the most recent samples. Pure; describes behaviour, never feelings.
import type { Sample } from "./sampler";

export type CueTone = "success" | "warning" | "neutral";

export interface LiveState {
  tone: CueTone;
  text: string;
}

export type CueKind = "nod" | "smile" | "attention";

export interface CueEvent {
  at_ms: number;
  kind: CueKind;
  text: string;
}

const MIN_SAMPLES = 3;
const AWAY_RUN = 6;
const SMILE_ON = 50;
const SMILE_QUIET = 5;
const FEED_SIZE = 8;

function trailingRun(samples: readonly Sample[], test: (s: Sample) => boolean): number {
  let n = 0;
  for (let i = samples.length - 1; i >= 0; i--) {
    const s = samples[i];
    if (!s || !test(s)) break;
    n++;
  }
  return n;
}

/** The one-line state shown at the top of the live cues. */
export function liveState(samples: readonly Sample[]): LiveState {
  if (samples.length < MIN_SAMPLES) return { tone: "neutral", text: "Getting ready" };
  if (trailingRun(samples, (s) => !s.face) >= MIN_SAMPLES) {
    return { tone: "warning", text: "Move into view of the camera" };
  }
  const away = trailingRun(samples, (s) => s.away);
  if (away >= AWAY_RUN) return { tone: "warning", text: `Looking away for ${away} seconds` };
  return { tone: "success", text: "Facing the patient" };
}

/** Feed events, newest first, at most 8: Nodded, Smiled, Looked back. */
export function cueEvents(samples: readonly Sample[]): CueEvent[] {
  const events: CueEvent[] = [];
  let quietSmile = 0;
  let awayRun = 0;
  for (const s of samples) {
    if (s.nod) events.push({ at_ms: s.at_ms, kind: "nod", text: "Nodded" });
    if (s.smile >= SMILE_ON) {
      if (quietSmile >= SMILE_QUIET) events.push({ at_ms: s.at_ms, kind: "smile", text: "Smiled" });
      quietSmile = 0;
    } else {
      quietSmile++;
    }
    if (s.away) {
      awayRun++;
    } else {
      if (awayRun >= AWAY_RUN) events.push({ at_ms: s.at_ms, kind: "attention", text: `Looked back after ${awayRun} seconds` });
      awayRun = 0;
    }
  }
  return events.reverse().slice(0, FEED_SIZE);
}
