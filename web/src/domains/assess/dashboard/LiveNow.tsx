"use client";

import { useEffect } from "react";
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
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { boardOrder, candidatesLabel, circuitStatus, recordingMissing, runningLine } from "@/domains/assess/dashboard/support";

/**
 * What is running, on the way past.
 *
 * The first circuit on the `/live` board, as the hero of the screen somebody
 * opens first. It renders nothing at all when nothing is running — a permanent empty
 * "Live now" panel teaches people to stop looking at it, which is the opposite
 * of what this is for.
 */
export function LiveNow({ orgSlug, onCount }: { orgSlug: string; onCount?: (running: number) => void }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const initial = useAsync((signal) => readLiveBoard(orgSlug, signal), [orgSlug]);
  const { session } = useSession();
  const stream = useEventStream<Board>(liveBoardStreamPath(orgSlug), {
    enabled: can(session, "run_circuits"),
  });
  const board = stream.data ?? initial.data;

  const circuits = boardOrder(board?.circuits ?? []);
  const running = circuits.length;
  useEffect(() => onCount?.(running), [onCount, running]);
  const first = circuits[0];
  if (stream.error && !first) return <Alert tone="danger">The live view is unavailable: {stream.error.message}</Alert>;
  if (!first) return null;
  const needsALook = recordingMissing(first) || (first.alerts ?? []).length > 0;

  const status = circuitStatus(first);
  // Keep the phase beside "Live": between stations, reading and consultation are what the room is doing.
  const chip = first.paused ? status : status === "Running" ? "Live" : `Live · ${status}`;
  const more = circuits.length > 1 ? ` (${circuits.length} running)` : "";
  const watch = (
    <ButtonLink key="watch" href={hrefFor("/live")} themeType="b2b" variant={w.hiring ? "commit" : "secondary"}>
      {`${w.liveBoardLink}${more}`}
    </ButtonLink>
  );
  const open = (
    <ButtonLink key="open" href={hrefFor(`/circuits/${first.circuit_id}`)} themeType="b2b" variant={w.hiring ? "secondary" : "commit"}>
      Open console
    </ButtonLink>
  );

  return (
    <B2CHero
      eyebrow="Running now"
      title={`${first.sitting_name} · ${first.circuit_name}`}
      action={
        <>
          {w.hiring ? [watch, open] : [open, watch]}
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
              {chip}
            </Badge>
          )}
          {first.remaining_seconds !== null && first.remaining_seconds !== undefined ? (
            <ExamClock
              secondsLeft={first.remaining_seconds}
              label={status}
              tick
              paused={first.paused}
            />
          ) : null}
        </div>
      }
    >
      {runningLine(first, w)}
      {(first.candidates ?? []).length > 0 ? ` · ${candidatesLabel(first)}` : ""}
    </B2CHero>
  );
}
