"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Alert, Badge, ButtonLink, EmptyState, Spinner, b2bTokens } from "@/foundation/ui";
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

  const rows = (state.data?.items ?? []).filter((row) => !row.ended);

  if (rows.length === 0) {
    if (!sayWhenEmpty) return null;
    return (
      <Section>
        <EmptyState
          title="Nothing is assigned to you."
          description="A circuit appears here when an administrator names you its supervisor."
        />
      </Section>
    );
  }

  // In progress first: a circuit that is running is somebody waiting.
  const ordered = rows.slice().sort((a, b) => Number(b.in_progress) - Number(a.in_progress));

  return (
    <Section>
      <div className={b2bTokens.b2bGroupedShell}>
        {ordered.map((row) => (
          <div key={row.circuit_id} className={b2bTokens.b2bGroupedRow}>
            <div className="min-w-0 flex-1">
              <p className={b2bTokens.b2bGroupedRowTitle}>{row.sitting_name}</p>
              <p className={b2bTokens.b2bGroupedRowSubtitle}>
                {row.circuit_name} · {row.mode} · {row.slot_count} station
                {row.slot_count === 1 ? "" : "s"}
                {row.scheduled_for ? ` · ${new Date(row.scheduled_for).toLocaleString()}` : ""}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <Badge variant={row.in_progress ? "success" : "info"} dot>
                {row.in_progress ? "In progress" : "Ready to run"}
              </Badge>
              <Link href={hrefFor(`/sittings/${row.sitting_id}`)} className={b2bTokens.b2bLinkMuted}>
                Sitting
              </Link>
              <ButtonLink
                href={hrefFor(`/circuits/${row.circuit_id}`)}
                themeType="b2b"
                variant={row.in_progress ? "commit" : "secondary"}
                size="sm"
              >
                {row.in_progress ? "Monitor" : "Open"}
              </ButtonLink>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

/** The heading this list lives under, wherever it is mounted. */
function Section({ children }: { children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className={b2bTokens.b2bEyebrow}>Assigned to you</h2>
      {children}
    </section>
  );
}
