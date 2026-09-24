"use client";

import { useState } from "react";
import { AsyncBoundary, Badge, Button, ButtonLink, Card, PageHeader, cn } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { useSession } from "@/foundation/session";
import { readSitting, type Sitting } from "@/domains/assess/api";
import { SittingEditForm } from "@/domains/assess/SittingEditForm";

/** One sitting and its circuits, with the way into each console. */
export function SittingDetail({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const userId = session?.user.id ?? null;
  const state = useAsync((signal) => readSitting(orgSlug, sittingId, signal), [orgSlug, sittingId]);
  const [editing, setEditing] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(sitting) => (
          <>
            <PageHeader
              title={sitting.name}
              description={
                sitting.scheduled_for
                  ? new Date(sitting.scheduled_for).toLocaleString()
                  : "Not scheduled"
              }
              actions={
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">{sitting.mode}</Badge>
                  <Badge tone={sitting.status === "live" ? "success" : "neutral"}>
                    {sitting.status}
                  </Badge>
                  <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
                    Edit
                  </Button>
                  <ButtonLink
                    size="sm"
                    variant="secondary"
                    href={hrefFor(`/sittings/${sitting.id}/results`)}
                  >
                    Results
                  </ButtonLink>
                  <ButtonLink size="sm" href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}>
                    Add a circuit
                  </ButtonLink>
                </div>
              }
            />

            {editing ? (
              <SittingEditForm
                orgSlug={orgSlug}
                sitting={sitting}
                onClose={() => setEditing(false)}
                onSaved={state.reload}
              />
            ) : null}

            <Card title="Circuits">
              {(sitting.circuits ?? []).length === 0 ? (
                <div className="flex flex-col items-start gap-3">
                  <p className="text-sm text-ink-muted">
                    No circuits yet. A sitting runs its circuits, so it needs at least one before
                    anybody can sit it.
                  </p>
                  <ButtonLink size="sm" href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}>
                    Add a circuit
                  </ButtonLink>
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {orderedCircuits(sitting, userId).map((circuit) => {
                    const mine = userId !== null && circuit.supervisor_user_id === userId;
                    return (
                      <li
                        key={circuit.id}
                        className={cn(
                          "flex flex-wrap items-center justify-between gap-3 py-3",
                          mine && "-mx-2 rounded-md bg-accent-subtle px-2",
                        )}
                      >
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate text-sm font-medium text-ink">{circuit.name}</p>
                            {mine ? <Badge tone="success">Your circuit</Badge> : null}
                          </div>
                          <p className="text-xs text-ink-subtle">
                            {(circuit.slots ?? []).length} slots
                            {circuit.supervisor_user_id && !mine ? " · Assigned to another supervisor" : ""}
                            {!circuit.supervisor_user_id ? " · No supervisor assigned" : ""}
                          </p>
                        </div>
                        <ButtonLink
                          size="sm"
                          variant={mine ? "primary" : "secondary"}
                          href={hrefFor(`/circuits/${circuit.id}`)}
                        >
                          Open console
                        </ButtonLink>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** The signed-in supervisor's circuits first, then the rest in the server's order. */
function orderedCircuits(sitting: Sitting, userId: string | null) {
  const circuits = sitting.circuits ?? [];
  if (!userId) return circuits;
  return [...circuits].sort((a, b) => {
    const aMine = a.supervisor_user_id === userId ? 0 : 1;
    const bMine = b.supervisor_user_id === userId ? 0 : 1;
    return aMine - bMine;
  });
}
