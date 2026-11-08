"use client";

import { useEffect, useState } from "react";
import { LuLogOut, LuMic, LuMicOff, LuUsers, LuVideo, LuVideoOff } from "react-icons/lu";
import { useLocalParticipant } from "@livekit/components-react";
import { cn } from "@/foundation/ui/cn";

const ROUND =
  "inline-flex h-11 w-11 items-center justify-center rounded-full transition-colors duration-200 ease-out motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent disabled:cursor-not-allowed disabled:opacity-50";
const ON = "bg-osce-canvas text-osce-ink-900 hover:bg-osce-navActive";
const OFF = "bg-osce-ink-900 text-white hover:bg-osce-ink-800";

export interface FloorControl {
  open: boolean;
  busy: boolean;
  onToggle: () => void;
}

/**
 * The room's one control bar: microphone, camera, and leave. The supervisor also gets the floor switch.
 *
 * The microphone opens by itself whenever the supervisor's rule lets this person speak (their turn, or
 * an open floor), and is disabled, with the reason beside the bar, whenever it does not.
 */
export function RoomBar({ micAllowed, onLeave, floor }: { micAllowed: boolean; onLeave: () => void; floor?: FloorControl }) {
  const { localParticipant, isMicrophoneEnabled, isCameraEnabled } = useLocalParticipant();
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    if (!micAllowed) return;
    localParticipant.setMicrophoneEnabled(true).catch(() => setProblem("Your browser is blocking your microphone."));
  }, [micAllowed, localParticipant]);

  const toggle = (device: "camera" | "microphone") => {
    setProblem(null);
    const next = device === "camera" ? !isCameraEnabled : !isMicrophoneEnabled;
    const pending =
      device === "camera" ? localParticipant.setCameraEnabled(next) : localParticipant.setMicrophoneEnabled(next);
    pending.catch(() => setProblem(`Your browser is blocking your ${device}.`));
  };

  return (
    <div className="sticky bottom-4 z-10 mt-5 flex flex-col items-center gap-2">
      {!micAllowed ? (
        <p aria-live="polite" className="flex items-center gap-1.5 text-assess-meta text-osce-ink-500">
          <LuMicOff aria-hidden className="h-3.5 w-3.5" />
          Muted by your supervisor
        </p>
      ) : null}
      {problem ? <p className="text-assess-meta text-osce-danger-text">{problem}</p> : null}
      <div className="flex items-center gap-1.5 rounded-full bg-osce-surface p-1.5 shadow-board-sheet ring-1 ring-osce-border-light">
        <button
          type="button"
          aria-label={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          title={micAllowed ? undefined : "Muted by your supervisor"}
          disabled={!micAllowed}
          onClick={() => toggle("microphone")}
          className={cn(ROUND, isMicrophoneEnabled ? ON : OFF)}
        >
          {isMicrophoneEnabled ? <LuMic aria-hidden className="h-[18px] w-[18px]" /> : <LuMicOff aria-hidden className="h-[18px] w-[18px]" />}
        </button>
        <button
          type="button"
          aria-label={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          onClick={() => toggle("camera")}
          className={cn(ROUND, isCameraEnabled ? ON : OFF)}
        >
          {isCameraEnabled ? <LuVideo aria-hidden className="h-[18px] w-[18px]" /> : <LuVideoOff aria-hidden className="h-[18px] w-[18px]" />}
        </button>
        {floor ? (
          <button
            type="button"
            disabled={floor.busy}
            aria-pressed={floor.open}
            onClick={floor.onToggle}
            className="ml-1 inline-flex h-11 items-center gap-2 rounded-full bg-osce-canvas px-4 text-assess-label font-medium text-osce-ink-900 transition-colors duration-200 ease-out hover:bg-osce-navActive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent disabled:opacity-50 motion-reduce:transition-none"
          >
            {floor.open ? <LuMicOff aria-hidden className="h-4 w-4" /> : <LuUsers aria-hidden className="h-4 w-4" />}
            {floor.open ? "Mute everyone" : "Open floor"}
          </button>
        ) : null}
        <button
          type="button"
          onClick={onLeave}
          className="ml-1 inline-flex h-11 items-center gap-2 rounded-full bg-osce-danger px-4 text-assess-label font-medium text-white transition-colors duration-200 ease-out hover:bg-osce-danger-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent motion-reduce:transition-none"
        >
          <LuLogOut aria-hidden className="h-4 w-4" />
          Leave
        </button>
      </div>
    </div>
  );
}
