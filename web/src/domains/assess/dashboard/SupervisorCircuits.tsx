"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { LuClipboardCheck } from "react-icons/lu";
import {
  Alert,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  Badge,
  ButtonLink,
  Spinner,
  b2bTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSupervisorCircuits, type SupervisorCircuitRow } from "@/domains/assess/dashboard/api";
import { circuitsBySitting, modeLabel, shortDate } from "@/domains/assess/dashboard/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * What a supervisor is here to do: the circuits they are named on.
 *
 * The old client assembled this by listing every session in the organisation
 * and filtering in the browser, which meant a supervisor's home screen loaded
 * the whole institution to show them two rows. One endpoint answers it, and it
 * answers only what is theirs.
 */
export function SupervisorCircuits({
  orgSlug,
  sayWhenEmpty = true,
  part = "list",
}: {
  /** "next" is the next-circuit card; "list" is "Circuits you lead". */
  part?: "next" | "list";
  orgSlug: string;
  /** False on a screen where an empty list is unremarkable. */
  sayWhenEmpty?: boolean;
}) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const state = useAsync((signal) => readSupervisorCircuits(orgSlug, signal), [orgSlug]);

  if (state.loading) return <Spinner />;
  if (state.error) return <Alert tone="danger">{errorMessage(state.error)}</Alert>;

  const all = state.data?.items ?? [];
  const rows = all.filter((row) => !row.ended);
  const lastEnded = all.filter((row) => row.ended).at(-1);

  if (part === "next") {
    const next = rows.slice().sort((a, b) => Number(b.in_progress) - Number(a.in_progress))[0];
    return next ? <NextCircuit row={next} /> : null;
  }
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

  // In progress first: a circuit that is running is somebody waiting.
  const ordered = rows.slice().sort((a, b) => Number(b.in_progress) - Number(a.in_progress));

  return (
    <Section>
      {circuitsBySitting(ordered).map((group) => {
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

/** "Your next circuit": the one running now, else the first to run. */
function NextCircuit({ row }: { row: SupervisorCircuitRow }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  return (
    <B2CGroupedSection eyebrow="Your next circuit">
    <div className="flex flex-col gap-2 p-4">
      <p className="text-osce-body font-semibold text-b2b-headline">{`${row.sitting_name} · ${row.circuit_name}`}</p>
      <p className="text-osce-meta text-b2b-muted">
        {`${row.scheduled_for ? `${new Date(row.scheduled_for).toLocaleString("en-GB", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }).replace(" at ", ", ")} · ` : ""}${modeLabel(row.mode, w)} · ${row.slot_count} station${row.slot_count === 1 ? "" : "s"}`}
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
