"use client";

import { useState } from "react";
import { LuMicOff } from "react-icons/lu";
import { HiOutlineMicrophone, HiOutlineVideoCamera, HiOutlineVideoCameraSlash } from "react-icons/hi2";
import { useLocalParticipant, useParticipants, useTracks, VideoTrack } from "@livekit/components-react";
import { Track } from "livekit-client";
import { Alert } from "@/foundation/ui";

/** Video layout ported from B2C LivekitHumanPracticeService.RoomContent. */
export function PeerVideoPanel({ role }: { role: "doctor" | "patient" }) {
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
  return (
    <div className="h-full flex flex-col relative">
      <div className="absolute top-4 right-4 z-10 flex gap-2 sm:gap-3">
        <button
          type="button"
          aria-label={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          title={isMicrophoneEnabled ? "Mute microphone" : "Unmute microphone"}
          aria-pressed={isMicrophoneEnabled}
          disabled={busy}
          onClick={() => void toggle("microphone")}
          className={`inline-flex h-11 w-11 items-center justify-center rounded-full border border-b2c-border transition-all shadow-lg ${
            isMicrophoneEnabled
              ? "bg-osce-surface hover:bg-b2c-secondary text-b2c-text-secondary"
              : "bg-osce-danger hover:bg-osce-danger/90 text-white border-transparent"
          }`}
        >
          {isMicrophoneEnabled ? (
            <HiOutlineMicrophone className="w-5 h-5" />
          ) : (
            <LuMicOff className="w-5 h-5" />
          )}
        </button>
        <button
          type="button"
          aria-label={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          title={isCameraEnabled ? "Turn camera off" : "Turn camera on"}
          aria-pressed={isCameraEnabled}
          disabled={busy}
          onClick={() => void toggle("camera")}
          className={`inline-flex h-11 w-11 items-center justify-center rounded-full border border-b2c-border transition-all shadow-lg ${
            isCameraEnabled
              ? "bg-osce-surface hover:bg-b2c-secondary text-b2c-text-secondary"
              : "bg-osce-danger hover:bg-osce-danger/90 text-white border-transparent"
          }`}
        >
          {isCameraEnabled ? (
            <HiOutlineVideoCamera className="w-5 h-5" />
          ) : (
            <HiOutlineVideoCameraSlash className="w-5 h-5" />
          )}
        </button>
      </div>
      {failure && <div className="absolute bottom-2 left-2 right-2 z-20"><Alert tone="warning">{failure}</Alert></div>}
      <div className="min-h-0 flex-1 p-2 bg-osce-ink-900 overflow-y-auto">
        <div className="flex flex-col gap-2 min-h-full">
          {participants.map((participant) => {
            const cameraTrack = tracks.find(
              (track) =>
                track.participant.identity === participant.identity &&
                track.source === Track.Source.Camera,
            );

            return (
              <div
                key={participant.identity}
                className="relative bg-osce-ink-800 rounded-lg overflow-hidden flex-1 min-h-[250px] flex items-center justify-center"
              >
                {cameraTrack && !cameraTrack.publication.isMuted ? (
                  <VideoTrack
                    trackRef={cameraTrack}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                ) : (
                  <div className="flex flex-col items-center text-osce-ink-500">
                    <HiOutlineVideoCameraSlash className="w-10 h-10 mb-2" />
                    <p className="text-osce-body">Camera Off</p>
                  </div>
                )}
                <div className="absolute bottom-2 left-2 bg-black/70 text-white px-2 py-1 rounded text-osce-body font-medium z-10 capitalize">
                  {participant.isLocal ? role : partnerRole}
                </div>
              </div>
            );
          })}
          {participants.length < 2 && (
            <div className="bg-osce-ink-800 rounded-lg flex items-center justify-center flex-1 min-h-[250px]">
              <div className="text-center text-osce-ink-400" role="status">
                <div className="animate-pulse">
                  <div className="w-12 h-12 bg-osce-ink-600 rounded-full mx-auto mb-3"></div>
                  {partnerDropped ? (
                    <>
                      <p className="text-osce-body font-medium text-white">Your partner&rsquo;s connection dropped</p>
                      <p className="text-osce-body">Waiting for them to reconnect...</p>
                    </>
                  ) : (
                    <p className="text-osce-body">Waiting for partner...</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
