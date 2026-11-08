"use client";

import { useEffect, useReducer } from "react";
import { LuMic, LuMicOff, LuStethoscope } from "react-icons/lu";
import {
  useIsSpeaking,
  useParticipants,
  useRoomContext,
  useTracks,
  VideoTrack,
  type TrackReference,
  type TrackReferenceOrPlaceholder,
} from "@livekit/components-react";
import { RoomEvent, Track, type Participant } from "livekit-client";
import { cn } from "@/foundation/ui/cn";
import { RoomBar, type FloorControl } from "@/domains/assess/room/RoomBar";
import {
  initials,
  roleOf,
  tileName,
  tileStatus,
  turnLine,
  type RoomPerson,
} from "@/domains/assess/room/tileState";

const MICROPHONE = 2; // LiveKit's TrackSource.MICROPHONE

/** Whether the server lets this participant publish a microphone. An empty source list means every source. */
function mayPublishMic(participant: Participant): boolean {
  const permissions = participant.permissions;
  if (!permissions?.canPublish) return false;
  const sources = permissions.canPublishSources ?? [];
  return sources.length === 0 || sources.includes(MICROPHONE);
}

export interface RoomControls {
  floor?: FloorControl;
  /** The supervisor's per-person microphone switch. */
  onMic?: (identity: string, allowed: boolean) => void;
  onLeave: () => void;
}

/**
 * The training room as a group video call: the patient first, then everyone else, all seen, only the
 * person whose turn it is (and the supervisor) heard. Must sit inside a connected `VoiceRoom`.
 */
export function RoomGrid({ controls }: { controls: RoomControls }) {
  const room = useRoomContext();
  const participants = useParticipants();
  const cameras = useTracks([Track.Source.Camera], { onlySubscribed: false });
  // Permissions are changed by the supervisor mid-call; the participant list does not re-render for that.
  const [, bump] = useReducer((n: number) => n + 1, 0);
  useEffect(() => {
    room.on(RoomEvent.ParticipantPermissionsChanged, bump);
    return () => {
      room.off(RoomEvent.ParticipantPermissionsChanged, bump);
    };
  }, [room]);

  const entries = participants.map((participant) => {
    const role = roleOf(participant.identity);
    const isSelf = participant.isLocal;
    const name = tileName({ role, name: participant.name, isSelf });
    const person: RoomPerson = { role, name, isSelf, micAllowed: role === "patient" || mayPublishMic(participant) };
    return { participant, person };
  });
  const patient = entries.find((entry) => entry.person.role === "patient");
  const others = entries.filter((entry) => entry.person.role !== "patient");
  const me = entries.find((entry) => entry.person.isSelf);
  const { line } = turnLine(entries.map((entry) => entry.person));
  const canControl = Boolean(controls.onMic);

  return (
    <div>
      <p aria-live="polite" className="mb-3 text-assess-label text-osce-ink-700">
        {line}
      </p>
      <div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 xl:grid-cols-3">
        {patient ? <Tile entry={patient} camera={cameraOf(cameras, patient.participant)} /> : <WaitingPatient />}
        {others.map((entry) => (
          <Tile
            key={entry.participant.identity}
            entry={entry}
            camera={cameraOf(cameras, entry.participant)}
            onMic={
              canControl && entry.person.role === "trainee" && !entry.person.isSelf
                ? () => controls.onMic?.(entry.participant.identity, !entry.person.micAllowed)
                : undefined
            }
          />
        ))}
      </div>
      <RoomBar micAllowed={me?.person.micAllowed ?? false} onLeave={controls.onLeave} floor={controls.floor} />
    </div>
  );
}

function cameraOf(tracks: TrackReferenceOrPlaceholder[], participant: Participant): TrackReference | null {
  for (const track of tracks) {
    if (track.participant.identity === participant.identity && track.publication && !track.publication.isMuted) {
      return track as TrackReference;
    }
  }
  return null;
}

function Tile({
  entry,
  camera,
  onMic,
}: {
  entry: { participant: Participant; person: RoomPerson };
  camera: TrackReference | null;
  onMic?: () => void;
}) {
  const { participant, person } = entry;
  const speaking = useIsSpeaking(participant);
  const status = tileStatus({ role: person.role, micAllowed: person.micAllowed, speaking });

  return (
    <div
      className={cn(
        "group relative flex aspect-video items-center justify-center overflow-hidden rounded-board-lg bg-osce-ink-900 ring-2 ring-transparent transition-shadow duration-200 ease-out motion-reduce:transition-none",
        status === "speaking" && "ring-osce-accent",
      )}
    >
      {camera ? (
        <VideoTrack trackRef={camera} className="h-full w-full object-cover" />
      ) : (
        <span
          aria-hidden
          className={cn(
            "flex h-16 w-16 items-center justify-center rounded-full text-lg font-semibold",
            person.role === "patient" ? "bg-osce-accent-subtle text-osce-accent" : "bg-osce-ink-800 text-osce-ink-400",
          )}
        >
          {person.role === "patient" ? <LuStethoscope className="h-6 w-6" /> : initials(person.name)}
        </span>
      )}
      <span className="absolute bottom-2.5 left-2.5 flex max-w-[calc(100%-1.25rem)] items-center gap-1.5 rounded-full bg-black/55 px-2.5 py-1 text-assess-chip font-medium text-white backdrop-blur-sm">
        {status === "muted" ? <LuMicOff aria-label="Muted" className="h-3 w-3 shrink-0 opacity-80" /> : null}
        <span className="truncate">{person.name}</span>
      </span>
      {onMic ? (
        <button
          type="button"
          onClick={onMic}
          aria-label={person.micAllowed ? `Mute ${person.name}` : `Let ${person.name} speak`}
          title={person.micAllowed ? `Mute ${person.name}` : `Let ${person.name} speak`}
          className="absolute right-2.5 top-2.5 inline-flex h-9 w-9 items-center justify-center rounded-full bg-black/55 text-white opacity-0 backdrop-blur-sm transition-opacity duration-150 ease-out hover:bg-black/70 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent group-focus-within:opacity-100 group-hover:opacity-100 motion-reduce:transition-none [@media(hover:none)]:opacity-100"
        >
          {person.micAllowed ? <LuMic aria-hidden className="h-4 w-4" /> : <LuMicOff aria-hidden className="h-4 w-4" />}
        </button>
      ) : null}
    </div>
  );
}

function WaitingPatient() {
  return (
    <div className="relative flex aspect-video items-center justify-center rounded-board-lg bg-osce-ink-900">
      <span aria-hidden className="flex h-16 w-16 items-center justify-center rounded-full bg-osce-ink-800 text-osce-ink-500">
        <LuStethoscope className="h-6 w-6" />
      </span>
      <span className="absolute bottom-2.5 left-2.5 rounded-full bg-black/55 px-2.5 py-1 text-assess-chip font-medium text-white/80 backdrop-blur-sm">
        Patient joining
      </span>
    </div>
  );
}
