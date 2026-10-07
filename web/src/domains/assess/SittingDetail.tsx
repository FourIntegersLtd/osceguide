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
  ConfirmModal,
  StepGuide,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { cancelSitting, deleteCircuit, readSitting, type Circuit, type Sitting } from "@/domains/assess/api";
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
  const [cancelling, setCancelling] = useState(false);
  const [deleting, setDeleting] = useState<Circuit | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  // The report's counts feed the steps. Every staff role reads it; a failure shows as one,
  // never as "0 marked, 0 decided".
  const report = useAsync((signal) => readSittingReport(orgSlug, sittingId, signal), [orgSlug, sittingId]);

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(sitting) => {
          const runCircuit = circuitToOpen(sitting.circuits ?? []);
          // The same permission as the cancel and delete routes (OrgAdmin). A cancelled
          // sitting takes no more changes, so its controls go with it.
          const manage = can(session, "schedule_sittings") && sitting.status !== "cancelled";
          const begun = (sitting.circuits ?? []).some((circuit) => circuit.started_at);
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
                  {manage ? (
                    <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setEditing(true)}>
                      Edit
                    </Button>
                  ) : null}
                  {manage && !begun ? (
                    <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setCancelling(true)}>
                      Cancel sitting
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
                  {manage ? (
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

            {/* A cancelled sitting has no next step to point at. */}
            {sitting.status === "cancelled" ? null : (
            <AsyncBoundary state={report}>
              {(data) => {
                const input: SittingStepsInput = {
                  scheduledFor: sitting.scheduled_for,
                  circuits: sitting.circuits ?? [],
                  counts: countsFromReport(data),
                  training: sitting.mode !== "exam",
                  can: { schedule: manage, signOff: can(session, "sign_off_results") },
                };
                const next = sittingNext(input);
                return (
                  <StepGuide steps={sittingSteps(input)} line={next.line}>
                    {next.actionable ? actions[next.id] : null}
                  </StepGuide>
                );
              }}
            </AsyncBoundary>
            )}

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
                  const row = (
                    <B2CGroupedRowLink
                      key={circuit.id}
                      className={manage && !circuit.started_at ? "min-w-0 flex-1" : undefined}
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
                  // Only a circuit that never started can go: a started one holds what was sat.
                  if (!manage || circuit.started_at) return row;
                  return (
                    <div key={circuit.id} className="flex items-center gap-2 pr-3">
                      {row}
                      <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setDeleting(circuit)}>
                        Delete
                      </Button>
                    </div>
                  );
                })}
              </B2CGroupedSection>
            )}

            <ConfirmModal
              isOpen={cancelling}
              title="Cancel this sitting?"
              message="Nobody can sit it once it is cancelled. It stays in the list, marked cancelled."
              confirmText="Cancel sitting"
              cancelText="Keep it"
              tone="danger"
              error={refused}
              onCancel={() => {
                setCancelling(false);
                setRefused(null);
              }}
              onConfirm={async () => {
                try {
                  await cancelSitting(orgSlug, sitting.id);
                  setCancelling(false);
                  setRefused(null);
                  state.reload();
                } catch (cause) {
                  setRefused(refusal(cause));
                }
              }}
            />
            <ConfirmModal
              isOpen={deleting !== null}
              title={`Delete ${deleting?.name ?? "this circuit"}?`}
              message="Its candidates and stations come off this sitting. Nothing has been sat on it yet."
              confirmText="Delete circuit"
              tone="danger"
              error={refused}
              onCancel={() => {
                setDeleting(null);
                setRefused(null);
              }}
              onConfirm={async () => {
                if (!deleting) return;
                try {
                  await deleteCircuit(orgSlug, deleting.id);
                  setDeleting(null);
                  setRefused(null);
                  state.reload();
                } catch (cause) {
                  setRefused(refusal(cause));
                }
              }}
            />
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

/** A cancel or delete refusal, by its code: something started since the page loaded. */
function refusal(cause: unknown): string {
  if (hasCode(cause, "sitting_locked")) {
    return "A circuit on this sitting has started, so it cannot be cancelled. End its circuits instead.";
  }
  if (hasCode(cause, "circuit_locked")) {
    return "This circuit has started, so it holds what was sat and cannot be deleted.";
  }
  return errorMessage(cause);
}

function OpenResults({ href }: { href: string }) {
  return (
    <ButtonLink themeType="b2b" size="sm" variant="commit" href={href}>
      Open results
    </ButtonLink>
  );
}
