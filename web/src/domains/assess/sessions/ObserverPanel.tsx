"use client";

import { useParticipants } from "@livekit/components-react";
import { Alert, Button } from "@/foundation/ui";
import { VoiceRoom } from "@/foundation/livekit";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import type { ObserverRoom } from "@/domains/assess/sessions/useCircuitRun";
import { assessMeta } from "@/foundation/ui/b2bTokens";

/**
 * Listening in on a running **exam** station: subscribe-only, because the backend token carries no
 * publish permission at all. A candidate cannot be prompted mid-consultation and the transcript stays
 * a record of what they said to the patient alone. A training circuit has a room instead
 * (`room/SupervisorRoom`). Drawn as the main side of the console's `SplitCard`.
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
    <section aria-label="Listen in" className="flex flex-col gap-3.5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 text-assess-label font-medium text-osce-ink-900">Listen in</h2>
        {observer.grant ? <span className={assessMeta}>Listening</span> : null}
      </div>
      {observer.failure ? <Alert tone="danger">{observer.failure}</Alert> : null}
      <p className={assessMeta}>
        Hear the consultation live. The candidate and patient cannot hear you.
      </p>
      {observer.grant ? (
        <VoiceRoom grant={observer.grant} audio={false} video={false} onDisconnected={(unexpected) => (unexpected ? observer.dropped() : observer.leave())}>
          <Occupants />
        </VoiceRoom>
      ) : null}
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
          title={live ? undefined : "Available while the circuit is running"}
          onClick={() => observer.join()}
        >
          Listen in
        </Button>
      )}
    </section>
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
        detail={agents.length > 0 ? "Here" : "Not here yet"}
        speaking={agents.some((agent) => agent.isSpeaking)}
      />
      {people.length === 0 ? (
        <Occupant label="The candidate" detail="Not here yet" speaking={false} />
      ) : (
        people.map((participant) => (
          <Occupant
            key={participant.sid}
            label={participant.name || "The candidate"}
            detail="Here"
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
