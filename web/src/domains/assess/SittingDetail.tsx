"use client";

import { AsyncBoundary, Badge, ButtonLink, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSitting } from "@/domains/assess/api";

/** One sitting and its circuits, with the way into each console. */
export function SittingDetail({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readSitting(orgSlug, sittingId, signal), [orgSlug, sittingId]);

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
                  {(sitting.circuits ?? []).map((circuit) => (
                    <li
                      key={circuit.id}
                      className="flex flex-wrap items-center justify-between gap-3 py-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-ink">{circuit.name}</p>
                        <p className="text-xs text-ink-subtle">
                          {(circuit.slots ?? []).length} slots
                        </p>
                      </div>
                      <ButtonLink
                        size="sm"
                        variant="secondary"
                        href={hrefFor(`/circuits/${circuit.id}`)}
                      >
                        Open console
                      </ButtonLink>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
