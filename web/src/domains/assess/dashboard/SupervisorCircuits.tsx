"use client";

import type { ReactNode } from "react";
import { LuClipboardCheck } from "react-icons/lu";
import {
  Alert,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  Badge,
  Spinner,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSupervisorCircuits } from "@/domains/assess/dashboard/api";

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
}: {
  orgSlug: string;
  /** False on a screen where an empty list is unremarkable. */
  sayWhenEmpty?: boolean;
}) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readSupervisorCircuits(orgSlug, signal), [orgSlug]);

  if (state.loading) return <Spinner />;
  if (state.error) return <Alert tone="danger">{errorMessage(state.error)}</Alert>;

  const all = state.data?.items ?? [];
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

  // In progress first: a circuit that is running is somebody waiting.
  const ordered = rows.slice().sort((a, b) => Number(b.in_progress) - Number(a.in_progress));

  return (
    <Section>
      {ordered.map((row) => (
        <B2CGroupedRowLink
          key={row.circuit_id}
          href={hrefFor(`/circuits/${row.circuit_id}`)}
          icon={LuClipboardCheck}
          title={`${row.sitting_name} · ${row.circuit_name}`}
          meta={`${row.mode} · ${row.slot_count} station${row.slot_count === 1 ? "" : "s"}${
            row.scheduled_for ? ` · ${new Date(row.scheduled_for).toLocaleString()}` : ""
          }`}
          trailing={
            <Badge variant={row.in_progress ? "success" : "info"} dot>
              {row.in_progress ? "In progress" : "Ready to run"}
            </Badge>
          }
        />
      ))}
    </Section>
  );
}

/** The heading this list lives under, wherever it is mounted. */
function Section({ children }: { children: ReactNode }) {
  return <B2CGroupedSection eyebrow="Assigned to you">{children}</B2CGroupedSection>;
}
