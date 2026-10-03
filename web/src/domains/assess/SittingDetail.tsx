"use client";

import { useState } from "react";
import { LuClipboardCheck } from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  Badge,
  Button,
  ButtonLink,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { useSession } from "@/foundation/session";
import { readSitting, type Circuit, type Sitting } from "@/domains/assess/api";
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
            <B2CPageHeader
              back={{ href: hrefFor("/sittings"), label: "Sittings" }}
              eyebrow={sitting.mode}
              title={sitting.name}
              subtitle={
                sitting.scheduled_for
                  ? new Date(sitting.scheduled_for).toLocaleString()
                  : "Not scheduled"
              }
              action={
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={sitting.status === "live" ? "success" : "neutral"} dot>
                    {sitting.status}
                  </Badge>
                  <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setEditing(true)}>
                    Edit
                  </Button>
                  <ButtonLink
                    themeType="b2b"
                    size="sm"
                    variant="secondary"
                    href={hrefFor(`/sittings/${sitting.id}/results`)}
                  >
                    Results
                  </ButtonLink>
                  <ButtonLink
                    themeType="b2b"
                    size="sm"
                    variant="commit"
                    href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}
                  >
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

            {(sitting.circuits ?? []).length === 0 ? (
              <B2CHero eyebrow="Circuits" title="No circuits yet">
                Add at least one circuit so candidates can take this sitting.
              </B2CHero>
            ) : (
              <B2CGroupedSection eyebrow="Circuits">
                {orderedCircuits(sitting, userId).map((circuit) => {
                  const mine = userId !== null && circuit.supervisor_user_id === userId;
                  return (
                    <B2CGroupedRowLink
                      key={circuit.id}
                      href={hrefFor(`/circuits/${circuit.id}`)}
                      icon={LuClipboardCheck}
                      title={circuit.name}
                      meta={[
                        circuitState(circuit),
                        `${circuit.trainee_count} ${circuit.trainee_count === 1 ? "trainee" : "trainees"}`,
                        circuit.supervisor_user_id
                          ? `Led by ${circuit.supervisor_name ?? "another supervisor"}`
                          : "No supervisor assigned",
                      ].join(" · ")}
                      trailing={
                        mine ? (
                          <Badge variant="success" dot>Your circuit</Badge>
                        ) : circuit.started_at && !circuit.ended_at ? (
                          <Badge variant="success" dot>Running</Badge>
                        ) : undefined
                      }
                    />
                  );
                })}
              </B2CGroupedSection>
            )}
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

/** Where a circuit is: waiting, running since a time, or finished. */
function circuitState(circuit: Circuit): string {
  if (circuit.ended_at) return "Finished";
  if (circuit.started_at) return `Running since ${new Date(circuit.started_at).toLocaleTimeString()}`;
  return "Not started";
}
