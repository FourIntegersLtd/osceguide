"use client";

import { boardBtn } from "@/foundation/ui/boardKit";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { Alert, Badge, b2bTokens, cn } from "@/foundation/ui";
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
 *
 * In a hire workspace the hero is the HireHome board's (title, one line, one button); its phase chip, clock and
 * "Open console" are drawn into `statusHost`, a strip under the board's content, so no real control disappears.
 */
export function LiveNow({ orgSlug, onCount, statusHost }: { orgSlug: string; onCount?: (running: number) => void; statusHost?: HTMLElement | null }) {
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
  if (w.hiring) {
    // HireHome board: the sitting running now, how many candidates are on stations across its circuits, one way in.
    // The phase chip, the clock and Open console are real, so they stay beside the board's button.
    const sitting = circuits.filter((c) => c.sitting_id === first.sitting_id);
    const people = sitting.reduce((n, c) => n + (c.candidates ?? []).length, 0);
    const who = first.supervisor?.name ?? first.supervisor?.email;
    const line = [`${people} ${people === 1 ? w.trainee : w.trainees} on stations`, who ? `${w.Supervisor}: ${who}` : null].filter(Boolean).join(" · ");
    const details = (
        <div role="group" className="flex flex-wrap items-center gap-2.5" aria-label="Running now status">
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
            <ExamClock secondsLeft={first.remaining_seconds} label={status} tick paused={first.paused} />
          ) : null}
          <Link href={hrefFor(`/circuits/${first.circuit_id}`)} className={boardBtn()}>
            Open console
          </Link>
        </div>
    );
    return (
      <>
      <section aria-label="Running now" className="box-border flex flex-wrap items-center justify-between gap-5 rounded-panel border border-osce-accent bg-assess-hero-live-bg p-6">
        <div>
          <div className={b2bTokens.assessEyebrow}>Running now</div>
          <h2 className="mt-1 text-assess-hero font-semibold text-osce-ink-900">{first.sitting_name}</h2>
          <div className={b2bTokens.assessMeta}>{line}</div>
        </div>
        <Link href={hrefFor("/live")} className={boardBtn()}>
          {`${w.liveBoardLink}${more}`}
        </Link>
      </section>
      {statusHost ? createPortal(details, statusHost) : details}
      </>
    );
  }

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
          Open console
        </Link>
      </BoardRow>
    </BoardSection>
  );
}
