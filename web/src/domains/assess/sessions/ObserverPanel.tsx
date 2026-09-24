"use client";

import { useParticipants } from "@livekit/components-react";
import { HiMiniSignal, HiOutlineEye } from "react-icons/hi2";
import { Alert, Button } from "@/foundation/ui";
import { VoiceRoom } from "@/foundation/livekit";
import { ExamClock } from "@/capabilities/attempt-runner";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import type { ObserverRoom } from "@/domains/assess/sessions/useCircuitRun";
import { phaseLabel } from "@/domains/assess/sessions/support";
import { ObserverVideoGrid } from "@/domains/assess/sessions/ObserverVideoGrid";

/**
 * Listening in on a running station — subscribe-only in an **exam**, where the
 * backend token carries no publish permission at all: a candidate cannot be
 * prompted mid-consultation and the transcript stays a record of what they
 * said to the patient alone.
 *
 * A **training** circuit's grant relaxes that on purpose
 * (`sittings/service_join.py:observer_token`), and `RoomGrant.can_publish`
 * says so — the retiring runner let a supervisor demonstrate on camera while
 * a trainee practised, and a training circuit carries no result a prompted
 * answer could corrupt. `ObserverVideoGrid` renders only then; the text-only
 * occupant list below is what an exam circuit still gets.
 */
export function ObserverPanel({
  data,
  observer,
}: {
  data: CircuitConsole;
  observer: ObserverRoom;
}) {
  const circuit = data.circuit;
  const live = circuit.started_at !== null && circuit.ended_at === null;

  return (
    <div className="overflow-hidden rounded-lg border border-b2b-border bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-b2b-border px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <HiMiniSignal
            className={`h-4 w-4 shrink-0 ${observer.grant ? "text-b2b-success-icon" : "text-b2b-icon"}`}
            aria-hidden
          />
          <span className="text-osce-body font-semibold text-b2b-headline">The room</span>
          <span className="text-osce-caption text-b2b-icon">
            {observer.grant ? "Listening" : "Not connected"}
          </span>
        </div>

        {observer.grant ? (
          <Button themeType="b2b" variant="secondary" size="sm" onClick={observer.leave}>
            Stop listening
          </Button>
        ) : (
          <Button
            themeType="b2b"
            variant="commit"
            size="sm"
            isLoading={observer.joining}
            disabled={!live}
            title={live ? undefined : "The circuit is not running"}
            onClick={() => void observer.join()}
          >
            <HiOutlineEye className="h-4 w-4 shrink-0" aria-hidden /> Listen in
          </Button>
        )}
      </div>

      <div className="space-y-3 p-4 sm:p-5">
        {observer.failure ? <Alert tone="danger">{observer.failure}</Alert> : null}

        {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
          <ExamClock
            secondsLeft={circuit.remaining_seconds}
            label={phaseLabel(circuit.phase)}
            tick
            paused={circuit.paused}
          />
        ) : null}

        {observer.grant ? (
          (() => {
            const canPublish = observer.grant.can_publish === true;
            return (
              <VoiceRoom
                grant={observer.grant}
                audio={canPublish}
                video={canPublish}
                onDisconnected={() => observer.leave()}
              >
                {canPublish ? <ObserverVideoGrid /> : <Occupants />}
              </VoiceRoom>
            );
          })()
        ) : (
          <p className="text-osce-caption leading-relaxed text-b2b-mid">
            You can hear the consultation without being heard in it. Nothing you do here reaches
            the candidate or the patient.
          </p>
        )}
      </div>
    </div>
  );
}

/** Who is actually in the room, which is the question a late patient raises. */
function Occupants() {
  const participants = useParticipants();
  const agents = participants.filter((participant) => participant.identity.startsWith("agent-"));
  const people = participants.filter(
    (participant) =>
      !participant.identity.startsWith("agent-") && !participant.identity.startsWith("observer-"),
  );

  return (
    <ul className="divide-y divide-b2b-border rounded-lg border border-b2b-border">
      <Occupant
        label="The patient"
        detail={agents.length > 0 ? "In the room" : "Not in the room yet"}
        speaking={agents.some((agent) => agent.isSpeaking)}
        present={agents.length > 0}
      />
      {people.length === 0 ? (
        <Occupant label="The candidate" detail="Not in the room yet" speaking={false} present={false} />
      ) : (
        people.map((participant) => (
          <Occupant
            key={participant.sid}
            label={participant.name || "The candidate"}
            detail="In the room"
            speaking={participant.isSpeaking}
            present
          />
        ))
      )}
    </ul>
  );
}

function Occupant({
  label,
  detail,
  speaking,
  present,
}: {
  label: string;
  detail: string;
  speaking: boolean;
  present: boolean;
}) {
  return (
    <li className="flex items-center justify-between gap-3 px-3 py-2.5">
      <div className="flex min-w-0 items-center gap-2">
        <span
          className={`h-2 w-2 shrink-0 rounded-full ${
            speaking ? "bg-b2b-success-icon" : present ? "bg-b2b-accent/60" : "bg-b2b-subtle"
          }`}
          aria-hidden
        />
        <span className="truncate text-osce-caption font-medium text-b2b-headline">{label}</span>
      </div>
      <span className="shrink-0 text-osce-caption text-b2b-mid">
        {speaking ? "Speaking" : detail}
      </span>
    </li>
  );
}
