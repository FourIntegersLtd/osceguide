"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LuDoorOpen, LuLogOut } from "react-icons/lu";
import { Alert, Badge, Button, Spinner } from "@/foundation/ui";
import { AgentTile, VoiceRoom, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { ExamClock } from "@/capabilities/attempt-runner";
import { joinCircuit, type MySitting } from "@/domains/assess/trainee/api";
import { joinFailureCopy, phaseLabel } from "@/domains/assess/trainee/support";

/**
 * A candidate in the room, and the way in.
 *
 * One implementation, used by the overview's live banner and by the sitting's
 * own page, because a candidate who joins from two places must not get two
 * behaviours. The retiring arm had a join page, a live-session component and a
 * set of pre-join states between them — ~430 lines to answer "am I allowed in
 * yet?", which the backend now answers with `can_join`.
 *
 * There is no supervisor video here: a candidate's room is the patient and
 * the candidate.
 */
export function JoinRoom({ sitting, onLeft }: { sitting: MySitting; onLeft?: () => void }) {
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Which circuit this person walked out of, rather than a flag that then has
  // to be cleared: a later circuit is a different id, so "have I left?" is
  // derived and there is no effect resetting state on the way in.
  const [leftCircuit, setLeftCircuit] = useState<string | null>(null);
  const left = leftCircuit === sitting.circuit_id;
  const mic = useMicPreflight(sitting.can_join);
  const attempted = useRef(false);

  const join = useCallback(async () => {
    setJoining(true);
    setError(null);
    try {
      // Mic permission is asked for, but a refusal must not stop the join: the
      // room existing is what matters (see below), and a candidate with no
      // microphone in the room can still be helped.
      if (mic.status !== "ready") await mic.request().catch(() => undefined);
      setGrant(await joinCircuit(sitting.circuit_id));
    } catch (cause) {
      setError(joinFailureCopy(cause));
    } finally {
      setJoining(false);
    }
  }, [mic, sitting.circuit_id]);

  /**
   * Join as soon as the backend allows it, during reading — do not wait for the
   * candidate to press a button when the consultation starts.
   *
   * The circuit dispatches its patient on the server's clock when the reading
   * phase ends, not when somebody joins. If nobody has opened the LiveKit room
   * by then the dispatch hits a room that does not exist, the transition errors,
   * and the circuit sits overdue for ever — it cannot even be ended, because the
   * same sweep runs on `end_circuit`. That cost two failed exam-day runs.
   *
   * The join token needs only a live circuit and carries no phase condition, so
   * joining during reading is both allowed and what a real candidate does.
   */
  useEffect(() => {
    if (!sitting.can_join || grant || joining || left || attempted.current) return;
    attempted.current = true;
    void join();
  }, [sitting.can_join, grant, joining, left, join]);

  // A candidate who left deliberately may come back in by hand; a circuit that
  // closes makes the automatic join eligible again for the next one.
  useEffect(() => {
    if (!sitting.can_join) attempted.current = false;
  }, [sitting.can_join]);

  if (grant) {
    return (
      <VoiceRoom
        grant={grant}
        onError={(cause) => {
          // A room that will not connect is said, not swallowed: leave it so Join is offered again.
          setGrant(null);
          setError(joinFailureCopy(cause));
          attempted.current = false;
        }}
        onDisconnected={(unexpected) => {
          setGrant(null);
          // An unexpected drop should re-join: the room has to stay occupied
          // for the patient dispatch to land.
          if (unexpected) attempted.current = false;
        }}
      >
        <div className="flex flex-col items-center gap-4">
          {mic.message ? <Alert tone="danger">{mic.message} The patient cannot hear you until it works.</Alert> : null}
          <Clock sitting={sitting} />
          <AgentTile name="Your patient" className="w-full max-w-sm" />
          <Button
            themeType="b2b"
            variant="danger"
            onClick={() => {
              setLeftCircuit(sitting.circuit_id);
              setGrant(null);
              onLeft?.();
            }}
          >
            <LuLogOut className="h-4 w-4" aria-hidden />
            Leave the room
          </Button>
        </div>
      </VoiceRoom>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {sitting.can_join && mic.message ? <Alert tone="warning">{mic.message}</Alert> : null}

      <div className="flex flex-wrap items-center gap-2">
        <Clock sitting={sitting} />
        {sitting.paused ? <Badge tone="warning">Paused</Badge> : null}
        {sitting.can_join ? (
          <Button themeType="b2b" variant="commit" onClick={() => join()} disabled={joining}>
            {joining ? <Spinner className="text-current" /> : <LuDoorOpen className="h-4 w-4" aria-hidden />}
            {left ? "Re-join" : "Join"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

/**
 * The clock, when the server is running one.
 *
 * `remaining_seconds` is read and rendered; nothing here counts. A browser
 * that keeps its own authoritative clock is a browser that disagrees with the
 * exam hall after one sleeping laptop.
 */
function Clock({ sitting }: { sitting: MySitting }) {
  if (sitting.remaining_seconds === null || sitting.remaining_seconds === undefined) return null;
  return (
    <ExamClock
      secondsLeft={sitting.remaining_seconds}
      label={phaseLabel(sitting.phase)}
      tick
      paused={sitting.paused}
    />
  );
}
