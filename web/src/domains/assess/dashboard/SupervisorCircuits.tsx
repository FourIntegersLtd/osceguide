"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { b2bTokens, cn } from "@/foundation/ui";
import { boardBtn, boardCard, boardChip } from "@/foundation/ui/boardKit";
import { BoardRow, BoardSection, RowText } from "@/domains/assess/dashboard/BoardParts";
import { useSurface } from "@/capabilities";
import type { SupervisorCircuitRow } from "@/domains/assess/dashboard/api";
import { circuitsBySitting, longWhen, modeLabel, shortDate } from "@/domains/assess/dashboard/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * What a supervisor is here to do: the circuits they are named on.
 *
 * The old client assembled this by listing every session in the organisation
 * and filtering in the browser, which meant a supervisor's home screen loaded
 * the whole institution to show them two rows. One endpoint answers it, and it
 * answers only what is theirs. The caller reads once and hands the rows to this list and to `NextCircuit`.
 */
export function SupervisorCircuits({
  rows: all,
  sayWhenEmpty = true,
}: {
  rows: readonly SupervisorCircuitRow[];
  /** False on a screen where an empty list is unremarkable. */
  sayWhenEmpty?: boolean;
}) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();

  const rows = all.filter((row) => !row.ended);
  const lastEnded = all.filter((row) => row.ended).at(-1);

  if (rows.length === 0) {
    if (!sayWhenEmpty) return null;
    return (
      <Section>
        <BoardRow>
          <RowText title="Nothing is assigned to you right now." meta="A circuit appears here when an administrator names you its supervisor." />
        </BoardRow>
        {lastEnded ? (
          <BoardRow href={hrefFor(`/circuits/${lastEnded.circuit_id}`)}>
            <RowText title="Your last ended circuit" meta={`${lastEnded.sitting_name} · ${lastEnded.circuit_name}`} />
          </BoardRow>
        ) : null}
      </Section>
    );
  }

  // The next circuit has its own card; this lists the rest, grouped by sitting.
  const rest = nextFirst(all).slice(1);
  if (rest.length === 0) return null;

  return (
    <Section>
      {circuitsBySitting(rest).map((group) => {
        const first = group.rows[0];
        if (!first) return null;
        const live = group.rows.some((row) => row.in_progress);
        const date = shortDate(first.scheduled_for);
        return (
          <BoardRow key={group.sittingId} href={hrefFor(group.rows.length === 1 ? `/circuits/${first.circuit_id}` : `/sittings/${group.sittingId}`)}>
            <RowText title={group.title} meta={[date, modeLabel(first.mode, w)].filter(Boolean).join(" · ")} />
            <span className={boardChip(live ? "ok" : "info")}>{live ? "In progress" : "Scheduled"}</span>
          </BoardRow>
        );
      })}
    </Section>
  );
}

/** Circuits not yet ended, the one running now first: a running circuit is somebody waiting. */
function nextFirst(all: readonly SupervisorCircuitRow[]): SupervisorCircuitRow[] {
  return all.filter((row) => !row.ended).sort((a, b) => Number(b.in_progress) - Number(a.in_progress));
}

/** The heading this list lives under, wherever it is mounted. */
function Section({ children }: { children: ReactNode }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  return (
    <BoardSection
      title="Circuits you lead"
      aside={
        <Link href={hrefFor("/sittings")} className={cn(b2bTokens.b2bLink, "text-assess-label")}>
          {`All ${w.sittings}`}
        </Link>
      }
    >
      {children}
    </BoardSection>
  );
}

/** "Your next circuit": the one running now, else the first to run. Nothing when none is left. */
export function NextCircuit({ rows }: { rows: readonly SupervisorCircuitRow[] }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const row = nextFirst(rows)[0];
  if (!row) return null;
  const when = longWhen(row.scheduled_for);
  return (
    <>
      <section aria-label="Your next circuit" className={cn(boardCard, "flex flex-wrap items-center gap-5 p-6")}>
        <div className="min-w-0 flex-[1_1_320px]">
          <div className={b2bTokens.assessEyebrow}>Your next circuit</div>
          <div className="mb-1 mt-1.5 text-assess-section font-semibold">{`${row.sitting_name} · ${row.circuit_name}`}</div>
          <div className={b2bTokens.assessMeta}>
            {[when, modeLabel(row.mode, w), `${row.slot_count} station${row.slot_count === 1 ? "" : "s"}`].filter(Boolean).join(" · ")}
          </div>
        </div>
        <Link href={hrefFor(`/circuits/${row.circuit_id}`)} className={boardBtn("primary")}>
          Open the console
        </Link>
      </section>
      <p className={cn(b2bTokens.assessMeta, "-mt-3")}>
        The console opens when the {w.sitting} starts. Any staff member can run any circuit on the day; reviewing stays with the circuit&apos;s {w.supervisor}.
      </p>
    </>
  );
}
