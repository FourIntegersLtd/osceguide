"use client";

import { useState } from "react";
import { LuMicOff } from "react-icons/lu";
import { HiOutlineMicrophone, HiOutlineVideoCamera, HiOutlineVideoCameraSlash } from "react-icons/hi2";
import { useLocalParticipant, useParticipants, useTracks, VideoTrack } from "@livekit/components-react";
import { Track } from "livekit-client";
import { Alert } from "@/foundation/ui";

/**
 * The supervisor's tile grid, training circuits only.
 *
 * Mounted instead of the text-only `Occupants` list when the observer grant
 * allows publishing (`RoomGrant.can_publish`, which `service_join.py` now
 * grants only to a training circuit's observer). The candidate never
 * publishes a camera — the consultation screen is audio-only by design, same
 * as the consumer arm — so this is really "the supervisor's own camera, plus
 * who else is in the room", not a symmetric video call. A candidate or the
 * AI patient still gets a tile; it just carries no video track and falls back
 * to the same presence/speaking indicator the subscribe-only view uses.
 */
export function ObserverVideoGrid() {
  const participants = useParticipants();
  const tracks = useTracks([Track.Source.Camera], { onlySubscribed: false });
  const { localParticipant, isMicrophoneEnabled, isCameraEnabled } = useLocalParticipant();
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const toggle = async (device: "camera" | "microphone") => {
    setBusy(true);
    setFailure(null);
    try {
      if (device === "camera") await localParticipant.setCameraEnabled(!isCameraEnabled);
      else await localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
    } catch {
      setFailure(`Could not access your ${device}. Check browser permissions and try again.`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          aria-label={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          title={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          aria-pressed={isMicrophoneEnabled}
          disabled={busy}
          onClick={() => void toggle("microphone")}
          className={`inline-flex h-9 w-9 items-center justify-center rounded-full border border-b2b-border transition-colors ${
            isMicrophoneEnabled
              ? "bg-b2b-surface text-b2b-icon hover:bg-b2b-subtle"
              : "border-transparent bg-osce-danger text-white hover:bg-osce-danger/90"
          }`}
        >
          {isMicrophoneEnabled ? (
            <HiOutlineMicrophone className="h-4 w-4" />
          ) : (
            <LuMicOff className="h-4 w-4" />
          )}
        </button>
        <button
          type="button"
          aria-label={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          title={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          aria-pressed={isCameraEnabled}
          disabled={busy}
          onClick={() => void toggle("camera")}
          className={`inline-flex h-9 w-9 items-center justify-center rounded-full border border-b2b-border transition-colors ${
            isCameraEnabled
              ? "bg-b2b-surface text-b2b-icon hover:bg-b2b-subtle"
              : "border-transparent bg-osce-danger text-white hover:bg-osce-danger/90"
          }`}
        >
          {isCameraEnabled ? (
            <HiOutlineVideoCamera className="h-4 w-4" />
          ) : (
            <HiOutlineVideoCameraSlash className="h-4 w-4" />
          )}
        </button>
      </div>

      {failure ? <Alert tone="warning">{failure}</Alert> : null}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {participants.map((participant) => {
          const isAgent = participant.identity.startsWith("agent-");
          const isObserver = participant.identity.startsWith("observer-");
          const label = isAgent ? "The patient" : isObserver ? "You" : participant.name || "The candidate";
          const cameraTrack = tracks.find(
            (track) =>
              track.participant.identity === participant.identity && track.source === Track.Source.Camera,
          );

          return (
            <div
              key={participant.identity}
              className="relative flex min-h-[160px] items-center justify-center overflow-hidden rounded-panel bg-osce-ink-900"
            >
              {cameraTrack && !cameraTrack.publication.isMuted ? (
                <VideoTrack trackRef={cameraTrack} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              ) : (
                <div className="flex flex-col items-center text-osce-ink-500">
                  <span
                    className={`h-3 w-3 rounded-full ${
                      participant.isSpeaking ? "bg-b2b-success-icon" : "bg-osce-ink-600"
                    }`}
                    aria-hidden
                  />
                  <p className="mt-2 text-osce-caption">{isAgent ? "Audio only" : "No camera"}</p>
                </div>
              )}
              <div className="absolute bottom-2 left-2 rounded bg-black/70 px-2 py-1 text-osce-caption font-medium text-white">
                {label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
