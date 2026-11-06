"use client";

import { useParticipants } from "@livekit/components-react";
import { Alert, Button } from "@/foundation/ui";
import { VoiceRoom } from "@/foundation/livekit";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import type { ObserverRoom } from "@/domains/assess/sessions/useCircuitRun";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardPad, boardChip } from "@/foundation/ui/boardKit";
import { ObserverVideoGrid } from "@/domains/assess/sessions/ObserverVideoGrid";
import { cardTitle } from "@/domains/assess/chrome";

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
    <div className={boardPad}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className={cardTitle}>The room</h2>
        <span className={boardChip(observer.grant ? "ok" : "neutral")}>
          {observer.grant ? "Listening" : "Not connected"}
        </span>
      </div>
      {observer.failure ? <Alert tone="danger">{observer.failure}</Alert> : null}
      <p className={assessMeta}>
        Listening in is subscribe-only: you can hear the consultation and cannot be heard in it. Nothing you do here
        reaches the candidate or the patient.
      </p>
      {observer.grant
        ? (() => {
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
        : null}
      {observer.grant ? (
        <Button themeType="b2b" variant="secondary" className="self-start" onClick={observer.leave}>
          Stop listening
        </Button>
      ) : (
        <Button
          themeType="b2b"
          variant="secondary"
          className="self-start"
          isLoading={observer.joining}
          disabled={!live}
          title={live ? undefined : "The circuit is not running"}
          onClick={() => observer.join()}
        >
          Listen in
        </Button>
      )}
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
    <ul>
      <Occupant
        label="The patient"
        detail={agents.length > 0 ? "In the room" : "Not in the room yet"}
        speaking={agents.some((agent) => agent.isSpeaking)}
      />
      {people.length === 0 ? (
        <Occupant label="The candidate" detail="Not in the room yet" speaking={false} />
      ) : (
        people.map((participant) => (
          <Occupant
            key={participant.sid}
            label={participant.name || "The candidate"}
            detail="In the room"
            speaking={participant.isSpeaking}
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
}: {
  label: string;
  detail: string;
  speaking: boolean;
}) {
  return (
    <li className="flex flex-wrap items-center gap-4 border-t border-osce-border-light py-2.5 text-assess-label text-osce-ink-900">
      <span className="flex-1">{label}</span>
      <span className={assessMeta}>{speaking ? "Speaking" : detail}</span>
    </li>
  );
}
