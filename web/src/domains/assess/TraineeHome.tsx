"use client";

import { useCallback, useState } from "react";
import { LuDoorOpen } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, PageHeader, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync, useEventStream } from "@/foundation/hooks";
import { AgentTile, VoiceRoom, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { ExamClock } from "@/capabilities/attempt-runner";
import { joinCircuit, readMySittings, type MySitting, type MySittings } from "@/domains/assess/api";

/**
 * What a trainee sees: the sittings they are rostered onto, pushed live.
 *
 * The join button appears when the backend says `can_join`, not when the
 * browser works it out from a status string. A trainee joining a slot that is
 * not theirs, or not yet live, is the kind of thing that has to be one
 * decision in one place.
 */
export function TraineeHome() {
  const initial = useAsync((signal) => readMySittings(signal), []);
  const stream = useEventStream<MySittings>("/api/v1/me/sittings/stream");
  const data = stream.data ?? initial.data;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Your sittings"
        description="Examinations and training sessions you are rostered onto."
        actions={
          <Badge tone={stream.connected ? "success" : "neutral"}>
            {stream.connected ? "Live" : "Updating"}
          </Badge>
        }
      />

      <AsyncBoundary state={initial}>
        {() => {
          const items = data?.items ?? [];
          if (items.length === 0) {
            return (
              <Card>
                <p className="text-sm text-ink-muted">
                  You are not rostered onto anything yet. Your institution will add you.
                </p>
              </Card>
            );
          }
          return (
            <ul className="flex flex-col gap-3">
              {items.map((sitting) => (
                <li key={`${sitting.id}-${sitting.circuit_id}`}>
                  <SittingCard sitting={sitting} />
                </li>
              ))}
            </ul>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function SittingCard({ sitting }: { sitting: MySitting }) {
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const mic = useMicPreflight(sitting.can_join);

  const join = useCallback(async () => {
    setJoining(true);
    setError(null);
    try {
      if (mic.status !== "ready") await mic.request();
      setGrant(await joinCircuit(sitting.circuit_id));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setJoining(false);
    }
  }, [mic, sitting.circuit_id]);

  if (grant) {
    return (
      <Card title={sitting.circuit_name}>
        <VoiceRoom grant={grant} onDisconnected={() => setGrant(null)}>
          <div className="flex flex-col items-center gap-4">
            {sitting.remaining_seconds !== null && sitting.remaining_seconds !== undefined && (
              <ExamClock
                secondsLeft={sitting.remaining_seconds}
                label={sitting.phase ?? "Station"}
              />
            )}
            <AgentTile name="Your patient" className="w-full max-w-sm" />
            <Button variant="danger" onClick={() => setGrant(null)}>
              Leave the room
            </Button>
          </div>
        </VoiceRoom>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex flex-col gap-3">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        {sitting.can_join && mic.message && <Alert tone="warning">{mic.message}</Alert>}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{sitting.name}</p>
            <p className="text-xs text-ink-subtle">
              {sitting.circuit_name}
              {sitting.scheduled_for
                ? ` · ${new Date(sitting.scheduled_for).toLocaleString()}`
                : ""}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {sitting.paused && <Badge tone="warning">Paused</Badge>}
            {sitting.live && <Badge tone="success">Live now</Badge>}
            {sitting.remaining_seconds !== null && sitting.remaining_seconds !== undefined && (
              <ExamClock secondsLeft={sitting.remaining_seconds} label={sitting.phase ?? "Now"} />
            )}
            {sitting.can_join && (
              <Button onClick={join} disabled={joining}>
                {joining ? <Spinner /> : <LuDoorOpen className="h-4 w-4" aria-hidden />}
                Join
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
