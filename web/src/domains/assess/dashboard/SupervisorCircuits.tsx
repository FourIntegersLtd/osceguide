"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { LuClipboardCheck } from "react-icons/lu";
import { B2CGroupedRow, B2CGroupedRowLink, B2CGroupedSection, Badge, ButtonLink, b2bTokens } from "@/foundation/ui";
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
        <B2CGroupedRow
          title="Nothing is assigned to you right now."
          meta="A circuit appears here when an administrator names you its supervisor."
        />
        {lastEnded ? (
          <B2CGroupedRowLink
            href={hrefFor(`/circuits/${lastEnded.circuit_id}`)}
            icon={LuClipboardCheck}
            title="Your last ended circuit"
            meta={`${lastEnded.sitting_name} · ${lastEnded.circuit_name}`}
          />
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
          <B2CGroupedRowLink
            key={group.sittingId}
            href={hrefFor(group.rows.length === 1 ? `/circuits/${first.circuit_id}` : `/sittings/${group.sittingId}`)}
            icon={LuClipboardCheck}
            title={group.title}
            meta={[date, modeLabel(first.mode, w)].filter(Boolean).join(" · ")}
            trailing={
              <Badge variant={live ? "success" : "info"} dot>
                {live ? "In progress" : "Scheduled"}
              </Badge>
            }
          />
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
    <B2CGroupedSection
      eyebrow="Circuits you lead"
      action={
        <Link href={hrefFor("/sittings")} className={b2bTokens.b2bLink}>
          {`All ${w.sittings}`}
        </Link>
      }
    >
      {children}
    </B2CGroupedSection>
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
    <B2CGroupedSection eyebrow="Your next circuit">
      <div className="flex flex-col gap-2 p-4">
        <p className="text-osce-body font-semibold text-b2b-headline">{`${row.sitting_name} · ${row.circuit_name}`}</p>
        <p className="text-osce-meta text-b2b-muted">
          {[when, modeLabel(row.mode, w), `${row.slot_count} station${row.slot_count === 1 ? "" : "s"}`].filter(Boolean).join(" · ")}
        </p>
        <div>
          <ButtonLink href={hrefFor(`/circuits/${row.circuit_id}`)} themeType="b2b" variant="commit">
            Open the console
          </ButtonLink>
        </div>
        <p className="text-osce-meta text-b2b-muted">
          The console opens when the {w.sitting} starts. Any staff member can run any circuit on the day; reviewing stays with the circuit&apos;s {w.supervisor}.
        </p>
      </div>
    </B2CGroupedSection>
  );
}
