"use client";

import { Alert, B2CHero, Badge, ButtonLink } from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { ExamClock } from "@/capabilities/attempt-runner";
import {
  liveBoardStreamPath,
  readLiveBoard,
  type LiveBoard as Board,
} from "@/domains/assess/dashboard/api";
import { boardOrder, candidatesLabel, circuitStatus, recordingMissing } from "@/domains/assess/dashboard/support";

/**
 * What is running, on the way past.
 *
 * The first circuit on the `/live` board, as the hero of the screen somebody
 * opens first. It renders nothing at all when nothing is running — a permanent empty
 * "Live now" panel teaches people to stop looking at it, which is the opposite
 * of what this is for.
 */
export function LiveNow({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const initial = useAsync((signal) => readLiveBoard(orgSlug, signal), [orgSlug]);
  const { session } = useSession();
  const stream = useEventStream<Board>(liveBoardStreamPath(orgSlug), {
    enabled: can(session, "run_circuits"),
  });
  const board = stream.data ?? initial.data;

  const circuits = boardOrder(board?.circuits ?? []);
  const first = circuits[0];
  if (stream.error && !first) return <Alert tone="danger">The live view is unavailable: {stream.error.message}</Alert>;
  if (!first) return null;
  const needsALook = recordingMissing(first) || (first.alerts ?? []).length > 0;

  return (
    <B2CHero
      eyebrow="Running now"
      title={`${first.sitting_name} · ${first.circuit_name}`}
      action={
        <>
          <ButtonLink href={hrefFor(`/circuits/${first.circuit_id}`)} themeType="b2b" variant="commit">
            Open console
          </ButtonLink>
          <ButtonLink href={hrefFor("/live")} themeType="b2b" variant="secondary">
            {circuits.length > 1 ? `Open the live board (${circuits.length} running)` : "Open the live board"}
          </ButtonLink>
        </>
      }
      aside={
        <div className="flex flex-wrap items-center gap-2">
          {needsALook ? (
            <Badge variant="danger" dot>
              Needs a look
            </Badge>
          ) : (
            <Badge variant={first.paused ? "warning" : "success"} dot>
              {circuitStatus(first)}
            </Badge>
          )}
          {first.remaining_seconds !== null && first.remaining_seconds !== undefined ? (
            <ExamClock
              secondsLeft={first.remaining_seconds}
              label={circuitStatus(first)}
              tick
              paused={first.paused}
            />
          ) : null}
        </div>
      }
    >
      {candidatesLabel(first)}
    </B2CHero>
  );
}
