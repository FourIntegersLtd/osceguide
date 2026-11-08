"use client";

import { boardBtn } from "@/foundation/ui/boardKit";
import { useEffect } from "react";
import { Alert, b2bTokens, cn } from "@/foundation/ui";
import { boardChip } from "@/foundation/ui/boardKit";
import { BoardRow, BoardSection, RowText } from "@/domains/assess/dashboard/BoardParts";
import Link from "next/link";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { ExamClock } from "@/capabilities/attempt-runner";
import {
  liveBoardStreamPath,
  readLiveBoard,
  type LiveBoard as Board,
  type LiveCircuit,
} from "@/domains/assess/dashboard/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { boardOrder, candidatesLabel, circuitStatus, recordingMissing, runningLine } from "@/domains/assess/dashboard/support";

/**
 * What is running, on the way past.
 *
 * The first circuit on the `/live` board, as the hero of the screen somebody
 * opens first. It renders nothing at all when nothing is running — a permanent empty
 * "Live now" panel teaches people to stop looking at it, which is the opposite
 * of what this is for.
 */
export function LiveNow({
  orgSlug,
  onCount,
  onFirst,
  bare = false,
}: {
  orgSlug: string;
  onCount?: (running: number) => void;
  /** The circuit that leads the board (or null), for a hero that draws it itself with `bare`. */
  onFirst?: (circuit: LiveCircuit | null) => void;
  bare?: boolean;
}) {
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
  useEffect(() => onFirst?.(first ?? null), [onFirst, first]);
  if (bare) return null;
  if (stream.error && !first) return <Alert tone="danger">The live view has stopped updating. Reload the page. If it keeps happening, tell support.</Alert>;
  if (!first) return null;
  const needsALook = recordingMissing(first) || (first.alerts ?? []).length > 0;

  const status = circuitStatus(first);
  // Keep the phase beside "Live": between stations, reading and consultation are what the room is doing.
  const more = circuits.length > 1 ? ` (${circuits.length} running)` : "";
  const line = runningLine(first, w) + ((first.candidates ?? []).length > 0 ? ` · ${candidatesLabel(first)}` : "");
  return (
    <BoardSection
      title="Running now"
      aside={
        <Link href={hrefFor("/live")} className={cn(b2bTokens.b2bLink, "text-assess-label")}>
          {`${w.liveBoardLink}${more}`}
        </Link>
      }
    >
      <BoardRow>
        <span className={boardChip(first.paused ? "warn" : "live")} title={status}>
          {needsALook ? "Needs a look" : first.paused ? status : status === "Running" ? "Live" : (
            <>
              Live<span className="max-[900px]:sr-only"> · {status}</span>
            </>
          )}
        </span>
        <RowText title={`${first.sitting_name} · ${first.circuit_name}`} meta={line} />
        {first.remaining_seconds !== null && first.remaining_seconds !== undefined ? (
          <span className={cn(b2bTokens.assessMeta, "tabular-nums")}>
            <ExamClock plain secondsLeft={first.remaining_seconds} label={status} tick paused={first.paused} /> left
          </span>
        ) : null}
        <Link href={hrefFor(`/circuits/${first.circuit_id}`)} className={boardBtn()}>
          {w.hiring ? "Open the console" : "Open console"}
        </Link>
      </BoardRow>
    </BoardSection>
  );
}
