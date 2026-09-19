"use client";

import Link from "next/link";
import { HiMiniSignal } from "react-icons/hi2";
import { Badge, b2bTokens } from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
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
 * The same board as `/live`, three rows of it, on the screen somebody opens
 * first. It renders nothing at all when nothing is running — a permanent empty
 * "Live now" panel teaches people to stop looking at it, which is the opposite
 * of what this is for.
 */
export function LiveNow({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const initial = useAsync((signal) => readLiveBoard(orgSlug, signal), [orgSlug]);
  const stream = useEventStream<Board>(liveBoardStreamPath(orgSlug));
  const board = stream.data ?? initial.data;

  const circuits = boardOrder(board?.circuits ?? []);
  if (circuits.length === 0) return null;

  const shown = circuits.slice(0, 3);

  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className={`${b2bTokens.b2bEyebrow} inline-flex items-center gap-2`}>
          <HiMiniSignal className="h-4 w-4 shrink-0 animate-pulse text-b2b-success-icon" aria-hidden />
          Running now
        </h2>
        <Link href={hrefFor("/live")} className={b2bTokens.b2bLink}>
          {circuits.length > shown.length ? `All ${circuits.length}` : "The board"}
        </Link>
      </div>

      <div className={b2bTokens.b2bGroupedShell}>
        {shown.map((circuit) => (
          <Link
            key={circuit.circuit_id}
            href={hrefFor(`/circuits/${circuit.circuit_id}`)}
            className={`${b2bTokens.b2bGroupedRow} hover:bg-b2b-cream`}
          >
            <div className="min-w-0 flex-1">
              <p className={b2bTokens.b2bGroupedRowTitle}>{circuit.circuit_name}</p>
              <p className={b2bTokens.b2bGroupedRowSubtitle}>
                {circuit.sitting_name} · {candidatesLabel(circuit)}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {recordingMissing(circuit) || (circuit.alerts ?? []).length > 0 ? (
                <Badge variant="danger" dot>
                  Needs a look
                </Badge>
              ) : (
                <Badge variant={circuit.paused ? "warning" : "success"} dot>
                  {circuitStatus(circuit)}
                </Badge>
              )}
              {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
                <ExamClock secondsLeft={circuit.remaining_seconds} label={circuitStatus(circuit)} />
              ) : null}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
