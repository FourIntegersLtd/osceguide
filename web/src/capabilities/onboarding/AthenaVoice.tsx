"use client";

import { useRef, useState } from "react";
import { LuMic, LuMicOff, LuPause, LuPlay } from "react-icons/lu";
import { RemoteTrackPublication } from "livekit-client";
import {
  BarVisualizer,
  useConnectionState,
  useLocalParticipant,
  useRoomContext,
  useVoiceAssistant,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { Button } from "@/foundation/ui";
import { agentStateLabel, micToggle, publishToAgent } from "@/foundation/livekit";
import { pauseToggle } from "@/capabilities/onboarding/onboardingModel";

/** The worker's names for these packets; `handlers.py` reads these exact words. */
const PAUSE = "pause";
const RESUME = "resume";

/** Athena's voice as bars, with pause and mute once the room is up. Must render inside `VoiceRoom`. */
export function AthenaVoice({ assistantName }: { assistantName: string }) {
  const { state, audioTrack } = useVoiceAssistant();
  const connected = useConnectionState() === ConnectionState.Connected;
  return (
    <div className="space-y-3 py-2">
      <div className="flex justify-center">
        {/* LiveKit's stylesheet sizes the visualiser to its parent, so the box is the parent's. */}
        <div className="h-12 w-40">
          <BarVisualizer
            state={state}
            barCount={7}
            trackRef={audioTrack}
            className="[--lk-fg:rgb(var(--color-accent))] [--lk-va-bar-bg:rgb(var(--color-ink)/0.2)] [--lk-va-bar-gap:8px] [--lk-va-bar-width:6px]"
            options={{ minHeight: 16 }}
          />
        </div>
        <p aria-live="polite" className="sr-only">
          {agentStateLabel(state, assistantName)}
        </p>
      </div>
      {connected && <VoiceControls assistantName={assistantName} audioTrack={audioTrack} />}
    </div>
  );
}

/**
 * Pause Athena, and mute or unmute me.
 *
 * Pausing silences her here (her track is switched off) and tells the worker,
 * which cuts off what she is saying and holds any scene clicked to meanwhile.
 * The microphone goes off with her, so nothing said during the pause starts a
 * reply, and comes back as it was on resume.
 */
function VoiceControls({
  assistantName,
  audioTrack,
}: {
  assistantName: string;
  audioTrack: ReturnType<typeof useVoiceAssistant>["audioTrack"];
}) {
  const room = useRoomContext();
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();
  const [paused, setPaused] = useState(false);
  const micBeforePause = useRef(true);
  const mic = micToggle(isMicrophoneEnabled, "me");
  const pause = pauseToggle(paused, assistantName);

  const togglePause = () => {
    const publication = audioTrack?.publication;
    if (publication instanceof RemoteTrackPublication) publication.setEnabled(!pause.next);
    if (pause.next) {
      micBeforePause.current = isMicrophoneEnabled;
      void localParticipant.setMicrophoneEnabled(false);
    } else {
      void localParticipant.setMicrophoneEnabled(micBeforePause.current);
    }
    void publishToAgent(room, pause.next ? PAUSE : RESUME, {});
    setPaused(pause.next);
  };

  return (
    <div role="group" aria-label={`${assistantName}'s voice`} className="flex justify-center gap-2">
      <Button size="sm" variant="secondary" onClick={togglePause}>
        {paused ? <LuPlay className="h-4 w-4" aria-hidden /> : <LuPause className="h-4 w-4" aria-hidden />}
        {pause.label}
      </Button>
      <Button
        size="sm"
        variant="secondary"
        disabled={paused}
        onClick={() => void localParticipant.setMicrophoneEnabled(mic.next)}
      >
        {isMicrophoneEnabled ? <LuMic className="h-4 w-4" aria-hidden /> : <LuMicOff className="h-4 w-4" aria-hidden />}
        {mic.label}
      </Button>
    </div>
  );
}
