"use client";

import { useState, type ReactNode } from "react";
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
  StepGuide,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { readSitting, type Circuit, type Sitting } from "@/domains/assess/api";
import { SittingEditForm } from "@/domains/assess/SittingEditForm";
import { readSittingReport } from "@/domains/assess/results/api";
import {
  circuitToOpen,
  countsFromReport,
  sittingNext,
  sittingSteps,
  type SittingNextId,
  type SittingStepsInput,
} from "@/domains/assess/sittingSteps";
import { sittingModeLabel, sittingRunning, sittingStatusLabel } from "@/domains/assess/support";
import { formatShortDateTime } from "@/foundation/format";

/** One sitting and its circuits, with the way into each console. */
export function SittingDetail({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const userId = session?.user.id ?? null;
  const state = useAsync((signal) => readSitting(orgSlug, sittingId, signal), [orgSlug, sittingId]);
  const [editing, setEditing] = useState(false);
  // The report's counts feed the steps. Every staff role reads it; a failure shows as one,
  // never as "0 marked, 0 decided".
  const report = useAsync((signal) => readSittingReport(orgSlug, sittingId, signal), [orgSlug, sittingId]);

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(sitting) => {
          const runCircuit = circuitToOpen(sitting.circuits ?? []);
          const actions: Partial<Record<SittingNextId, ReactNode>> = {
            schedule: (
              <Button themeType="b2b" size="sm" variant="commit" onClick={() => setEditing(true)}>
                Set a date
              </Button>
            ),
            circuits: (
              <ButtonLink themeType="b2b" size="sm" variant="commit" href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}>
                Add a circuit
              </ButtonLink>
            ),
            run: runCircuit ? (
              <ButtonLink themeType="b2b" size="sm" variant="commit" href={hrefFor(`/circuits/${runCircuit.id}`)}>
                Open the console
              </ButtonLink>
            ) : null,
            mark: <OpenResults href={hrefFor(`/sittings/${sitting.id}/results`)} />,
            decide: <OpenResults href={hrefFor(`/sittings/${sitting.id}/results`)} />,
            release: <OpenResults href={hrefFor(`/sittings/${sitting.id}/results`)} />,
          };
          return (
          <>
            <B2CPageHeader
              back={{ href: hrefFor("/sittings"), label: "Sittings" }}
              eyebrow={sittingModeLabel(sitting.mode)}
              title={sitting.name}
              subtitle={
                sitting.scheduled_for ? formatShortDateTime(sitting.scheduled_for) : "No date set"
              }
              action={
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={sittingRunning(sitting.status) ? "success" : "neutral"} dot>
                    {sittingStatusLabel(sitting.status)}
                  </Badge>
                  {can(session, "schedule_sittings") ? (
                    <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setEditing(true)}>
                      Edit
                    </Button>
                  ) : null}
                  <ButtonLink
                    themeType="b2b"
                    size="sm"
                    variant="secondary"
                    href={hrefFor(`/sittings/${sitting.id}/results`)}
                  >
                    Results
                  </ButtonLink>
                  {can(session, "schedule_sittings") ? (
                    <ButtonLink
                      themeType="b2b"
                      size="sm"
                      variant="commit"
                      href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}
                    >
                      Add a circuit
                    </ButtonLink>
                  ) : null}
                </div>
              }
            />

            <AsyncBoundary state={report}>
              {(data) => {
                const input: SittingStepsInput = {
                  scheduledFor: sitting.scheduled_for,
                  circuits: sitting.circuits ?? [],
                  counts: countsFromReport(data),
                  training: sitting.mode !== "exam",
                  can: { schedule: can(session, "schedule_sittings"), signOff: can(session, "sign_off_results") },
                };
                const next = sittingNext(input);
                return (
                  <StepGuide steps={sittingSteps(input)} line={next.line}>
                    {next.actionable ? actions[next.id] : null}
                  </StepGuide>
                );
              }}
            </AsyncBoundary>

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
          );
        }}
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

function OpenResults({ href }: { href: string }) {
  return (
    <ButtonLink themeType="b2b" size="sm" variant="commit" href={href}>
      Open results
    </ButtonLink>
  );
}
