"use client";

import { useCallback, useMemo, useState } from "react";
import { useAsync, useLocalPreference } from "@/foundation/hooks";
import { readNonverbal, type NonverbalRead } from "./api";
import { cueEvents, liveState } from "./cues";
import { nonverbalOff } from "./preference";
import { useNonverbalCapture } from "./useNonverbalCapture";

/**
 * Everything the consultation needs for non-verbal cues: the read (once), the consent and
 * on/off state, the capture, and the live state and feed worked out from its samples.
 * Capture runs only while consented, switched on and the room is live.
 */
export function useNonverbal(attemptId: string | null, isLive: boolean) {
  const state = useAsync<NonverbalRead | null>(
    (signal) => (attemptId ? readNonverbal(attemptId, signal) : Promise.resolve(null)),
    [attemptId],
  );
  const read = state.data;
  const off = useLocalPreference(nonverbalOff);
  const [consentOpen, setConsentOpen] = useState(false);
  const reload = state.reload;
  const active = Boolean(read?.supported && read.consented && !off && isLive);
  const capture = useNonverbalCapture({ attemptId, active, onRefused: reload });
  const live = useMemo(() => liveState(capture.samples), [capture.samples]);
  const events = useMemo(() => cueEvents(capture.samples), [capture.samples]);

  const turnOn = useCallback(() => {
    if (read?.consented) nonverbalOff.set(false);
    else setConsentOpen(true);
  }, [read?.consented]);
  const turnOff = useCallback(() => nonverbalOff.set(true), []);
  const closeConsent = useCallback(() => setConsentOpen(false), []);
  const granted = useCallback(() => {
    nonverbalOff.set(false);
    setConsentOpen(false);
    reload();
  }, [reload]);

  return { read, off, capture, live, events, turnOn, turnOff, consentOpen, closeConsent, granted, reload };
}

export type Nonverbal = ReturnType<typeof useNonverbal>;
