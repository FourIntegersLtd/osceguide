"use client";

import { useState } from "react";
import { LuMicOff, LuPhone } from "react-icons/lu";
import { HiOutlineMicrophone, HiOutlineVideoCamera, HiOutlineVideoCameraSlash } from "react-icons/hi2";
import { useLocalParticipant, useParticipants, useTracks, VideoTrack } from "@livekit/components-react";
import { Track } from "livekit-client";
import { Alert } from "@/foundation/ui";

/** The video layout for two people practising together. `onEnd` adds the hang-up button. */
export function PeerVideoPanel({ role, onEnd }: { role: "doctor" | "patient"; onEnd?: () => void }) {
  const participants = useParticipants();
  const tracks = useTracks([Track.Source.Camera, Track.Source.Microphone], { onlySubscribed: false });
  const { localParticipant, isMicrophoneEnabled, isCameraEnabled } = useLocalParticipant();
  const partnerRole = role === "doctor" ? "patient" : "doctor";
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // A partner who leaves ends the session, and the session screen says so
  // from the server's push. One who vanishes from the room while the session
  // still runs dropped their connection: say that instead of "waiting".
  const partnerHere = participants.some((participant) => !participant.isLocal);
  const [partnerSeen, setPartnerSeen] = useState(false);
  if (partnerHere && !partnerSeen) setPartnerSeen(true);
  const partnerDropped = partnerSeen && !partnerHere;
  const toggle = async (device: "camera" | "microphone") => {
    setBusy(true); setFailure(null);
    try {
      if (device === "camera") await localParticipant.setCameraEnabled(!isCameraEnabled);
      else await localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
    } catch { setFailure(`Could not access your ${device}. Check browser permissions and try again.`); }
    finally { setBusy(false); }
  };
  const partner = participants.find((participant) => !participant.isLocal);
  const cameraOf = (identity: string) => {
    const track = tracks.find((t) => t.participant.identity === identity && t.source === Track.Source.Camera);
    return track && !track.publication.isMuted ? track : null;
  };
  const partnerCamera = partner ? cameraOf(partner.identity) : null;
  const ownCamera = cameraOf(localParticipant.identity);
  // Like a phone call: a click on your corner tile gives each of you half the
  // stage, and a click on your half sends you back to the corner.
  const [split, setSplit] = useState(false);
  const cover = { width: "100%", height: "100%", objectFit: "cover" } as const;
  const tag = "absolute rounded-osce-md bg-osce-surface-inset/85 font-medium capitalize text-osce-ink-900";
  const ownName = localParticipant.name || role;
  const fullInitials = "h-20 w-20 text-osce-title sm:h-28 sm:w-28 sm:text-osce-display-sm lg:h-36 lg:w-36";
  // Half a phone stage is short: the circle has to fit above the controls.
  const halfInitials = "h-12 w-12 text-osce-subheading lg:h-28 lg:w-28 lg:text-osce-display-sm";
  const control =
    "inline-flex h-11 w-11 items-center justify-center rounded-osce-lg border transition-colors disabled:opacity-60";
  const controlOn = "border-osce-border bg-osce-nav-active text-osce-ink-900 hover:bg-osce-accent-subtle";
  const controlOff = "border-transparent bg-osce-danger text-white hover:bg-osce-danger/90";
  return (
    // One stage: the partner fills it, you sit in the corner, the controls along the bottom.
    // It is its own container, so the corner tile drops beside the controls only where both fit.
    <div className="relative h-full overflow-hidden bg-osce-canvas [container-type:inline-size]">
      <div className={`flex h-full ${split ? "flex-col gap-2 p-2" : ""}`}>
        <div className={`relative flex min-h-0 min-w-0 flex-1 items-center justify-center overflow-hidden ${split ? "rounded-osce-lg bg-osce-surface-inset" : ""}`}>
          {partnerCamera ? (
            <VideoTrack trackRef={partnerCamera} style={cover} />
          ) : partner ? (
            <div className="flex flex-col items-center gap-2 sm:gap-3">
              <Initials name={partner.name || partnerRole} className={split ? halfInitials : fullInitials} />
              <p className="text-osce-meta capitalize text-osce-ink-500 sm:text-osce-body">{partnerRole} · camera off</p>
            </div>
          ) : (
            <div className="text-center text-osce-ink-500" role="status">
              <div className="mx-auto mb-3 h-12 w-12 animate-pulse rounded-full bg-osce-nav-active" />
              {partnerDropped ? (
                <>
                  <p className="text-osce-body font-medium text-osce-ink-900">Your partner&rsquo;s connection dropped</p>
                  <p className="text-osce-body">Waiting for them to reconnect...</p>
                </>
              ) : (
                <p className="text-osce-body">Waiting for partner...</p>
              )}
            </div>
          )}
          {partner && <span className={`${tag} left-3 top-3 px-2 py-1 text-osce-meta`}>{partnerRole}</span>}
        </div>

        <button
          type="button"
          aria-label={split ? "Minimise your video" : "Expand your video"}
          title={split ? "Minimise your video" : "Expand your video"}
          aria-pressed={split}
          onClick={() => setSplit(!split)}
          className={
            split
              ? "relative flex min-h-0 min-w-0 flex-1 items-center justify-center overflow-hidden rounded-osce-lg bg-osce-surface-inset"
              : "absolute bottom-[4.25rem] right-3 flex h-20 w-28 items-center justify-center overflow-hidden rounded-osce-lg border border-osce-border bg-osce-nav-active transition-colors hover:border-osce-ink-500 sm:h-36 sm:w-56 [@container_(min-width:42rem)]:bottom-3"
          }
        >
          {ownCamera ? (
            <VideoTrack trackRef={ownCamera} style={cover} />
          ) : (
            <Initials
              name={ownName}
              className={split ? halfInitials : "h-10 w-10 text-osce-body sm:h-12 sm:w-12 sm:text-osce-subheading"}
            />
          )}
          <span className={`${tag} ${split ? "left-3 top-3 px-2 py-1 text-osce-meta" : "bottom-1.5 left-1.5 px-1.5 py-0.5 text-osce-caption"}`}>
            You
          </span>
        </button>
      </div>

      {failure && <div className="absolute left-3 right-3 top-3 z-20"><Alert tone="warning">{failure}</Alert></div>}

      <div className="absolute bottom-3 left-1/2 z-10 flex -translate-x-1/2 gap-2">
        <button
          type="button"
          aria-label={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          title={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          aria-pressed={isMicrophoneEnabled}
          disabled={busy}
          onClick={() => void toggle("microphone")}
          className={`${control} ${isMicrophoneEnabled ? controlOn : controlOff}`}
        >
          {isMicrophoneEnabled ? <HiOutlineMicrophone className="h-5 w-5" /> : <LuMicOff className="h-5 w-5" />}
        </button>
        <button
          type="button"
          aria-label={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          title={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          aria-pressed={isCameraEnabled}
          disabled={busy}
          onClick={() => void toggle("camera")}
          className={`${control} ${isCameraEnabled ? controlOn : controlOff}`}
        >
          {isCameraEnabled ? <HiOutlineVideoCamera className="h-5 w-5" /> : <HiOutlineVideoCameraSlash className="h-5 w-5" />}
        </button>
        {onEnd && (
          <button type="button" aria-label="End session" title="End session" onClick={onEnd} className={`${control} ${controlOff}`}>
            <LuPhone className="h-5 w-5 rotate-[135deg]" />
          </button>
        )}
      </div>
    </div>
  );
}

/** A person with their camera off: their initials in a quiet circle. */
function Initials({ name, className }: { name: string; className: string }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("");
  return (
    <span aria-hidden className={`flex items-center justify-center rounded-full bg-osce-nav-active font-semibold text-osce-ink-900 ${className}`}>
      {initials}
    </span>
  );
}
