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
import { useAsync, type AsyncState } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { listActiveTrainees, readSitting, type Circuit, type Sitting } from "@/domains/assess/api";
import { SittingActionDialog, type PendingSittingAction } from "@/domains/assess/SittingActions";
import { PendingCircuitsNotice } from "@/domains/assess/PendingCircuitsNotice";
import { SittingEditForm } from "@/domains/assess/SittingEditForm";
import { readSittingReport, type SittingReport } from "@/domains/assess/results/api";
import { readAllCohorts, resendInvitation } from "@/domains/assess/roster/api";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { TabStrip } from "@/domains/assess/team/chrome";
import {
  circuitToOpen,
  countsFromReport,
  sittingNext,
  sittingSteps,
  type SittingNextId,
  type SittingStepsInput,
} from "@/domains/assess/sittingSteps";
import { sittingModeLabel, sittingRunning, sittingStatusLabel } from "@/domains/assess/support";
import { formatShortDateTime, plural } from "@/foundation/format";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/** One sitting and its circuits, with the way into each console. */
export function SittingDetail({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const userId = session?.user.id ?? null;
  const state = useAsync((signal) => readSitting(orgSlug, sittingId, signal), [orgSlug, sittingId]);
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState<PendingSittingAction>(null);
  const [tab, setTab] = useState<SittingTab>("circuits");
  const cohorts = useAsync((signal) => readAllCohorts(orgSlug, signal), [orgSlug]);
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
            <PendingCircuitsNotice orgSlug={orgSlug} sittingId={sitting.id} onDone={state.reload} />
            <B2CPageHeader
              back={{ href: hrefFor("/sittings"), label: w.Sittings }}
              eyebrow={sittingModeLabel(sitting.mode)}
              title={sitting.name}
              subtitle={[
                sitting.scheduled_for ? formatShortDateTime(sitting.scheduled_for) : "No date set",
                sitting.cohort_id
                  ? `Year group: ${cohorts.data?.find((cohort) => cohort.id === sitting.cohort_id)?.name ?? "…"}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
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
                    <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setPending({ kind: "cancel" })}>
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
                </div>
              }
            />

            <SittingNextStep
              sitting={sitting}
              report={report}
              can={{ schedule: manage, signOff: can(session, "sign_off_results") }}
              actions={actions}
            />

            {editing ? (
              <SittingEditForm
                orgSlug={orgSlug}
                sitting={sitting}
                onClose={() => setEditing(false)}
                onSaved={state.reload}
              />
            ) : null}

            <TabStrip
              label="Sitting sections"
              active={tab}
              onSelect={setTab}
              tabs={[
                { key: "circuits", label: "Circuits", count: (sitting.circuits ?? []).length },
                { key: "candidates", label: "Candidates" },
                { key: "results", label: "Results so far" },
              ]}
            />

            {tab === "candidates" ? <CandidatesTab orgSlug={orgSlug} sitting={sitting} report={report} /> : null}
            {tab === "results" ? (
              <ResultsTab report={report} href={hrefFor(`/sittings/${sitting.id}/results`)} />
            ) : null}
            {tab !== "circuits" ? null : (sitting.circuits ?? []).length === 0 ? (
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
                        ...((circuit.slots ?? []).length > 0
                          ? [plural(new Set((circuit.slots ?? []).map((slot) => slot.station_version_id)).size, "station")]
                          : []),
                        `${circuit.trainee_count} ${circuit.trainee_count === 1 ? w.trainee : w.trainees}`,
                        circuit.supervisor_user_id
                          ? `Supervisor ${circuit.supervisor_name ?? "another supervisor"}`
                          : "No supervisor assigned",
                      ].join(" · ")}
                      trailing={
                        mine ? (
                          <Badge variant="success" dot>Your circuit</Badge>
                        ) : circuit.started_at && !circuit.ended_at ? (
                          <Badge variant="success" dot>Running</Badge>
                        ) : !circuit.started_at && circuit.supervisor_user_id && circuit.trainee_count > 0 ? (
                          <Badge variant="neutral" dot>Ready</Badge>
                        ) : undefined
                      }
                    />
                  );
                  // Only a circuit that never started can go: a started one holds what was sat.
                  if (!manage || circuit.started_at) return row;
                  return (
                    <div key={circuit.id} className="flex items-center gap-2 pr-3">
                      {row}
                      <ButtonLink themeType="b2b" size="sm" variant="secondary" href={hrefFor(`/circuits/${circuit.id}/edit`)}>
                        Edit
                      </ButtonLink>
                      <Button themeType="b2b" size="sm" variant="secondary" onClick={() => setPending({ kind: "delete", circuit })}>
                        Delete
                      </Button>
                    </div>
                  );
                })}
              </B2CGroupedSection>
            )}
            {tab === "circuits" && manage && (sitting.circuits ?? []).length > 0 ? (
              <div>
                <ButtonLink themeType="b2b" size="sm" variant="secondary" href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}>
                  Add a circuit
                </ButtonLink>
              </div>
            ) : null}
            {tab === "circuits" && manage ? (
              <p className="text-sm text-ink-muted">
                Cancel sitting is only before any circuit starts. A circuit can be deleted only if it never started.
              </p>
            ) : null}
            {tab === "circuits" && (sitting.circuits ?? []).length > 1 ? (
              <p className="text-sm text-ink-muted">
                {(sitting.circuits ?? []).length - 1} more circuits · supervisors see their own circuit first
              </p>
            ) : null}

            <SittingActionDialog
              orgSlug={orgSlug}
              sittingId={sitting.id}
              pending={pending}
              onClose={() => setPending(null)}
              onDone={state.reload}
            />
          </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

type SittingTab = "circuits" | "candidates" | "results";

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

/**
 * Everyone on the sitting: the people on its circuits (the report), each with their year group
 * and whether they have signed in (the roster), then invited people of the sitting's year group
 * who are not on a circuit yet, with the way to resend the invitation.
 */
function CandidatesTab({
  orgSlug,
  sitting,
  report,
}: {
  orgSlug: string;
  sitting: Sitting;
  report: AsyncState<SittingReport>;
}) {
  const roster = useAsync(
    async (signal) => ({
      trainees: await listActiveTrainees(orgSlug, signal),
      cohorts: await readAllCohorts(orgSlug, signal),
    }),
    [orgSlug],
  );
  const [sent, setSent] = useState<Record<string, string>>({});
  const resend = async (traineeId: string) => {
    try {
      await resendInvitation(orgSlug, traineeId);
      setSent((current) => ({ ...current, [traineeId]: "Invitation sent." }));
    } catch (cause) {
      setSent((current) => ({ ...current, [traineeId]: assessErrorMessage(cause) }));
    }
  };
  return (
    <AsyncBoundary state={roster}>
      {({ trainees, cohorts }) => (
        <AsyncBoundary state={report}>
          {(data) => {
            const byUser = new Map(trainees.filter((t) => t.user_id).map((t) => [t.user_id as string, t]));
            const onCircuit = new Set((data.candidates ?? []).map((candidate) => candidate.user_id));
            const yearOf = (cohortId: string | null | undefined) =>
              cohorts.find((cohort) => cohort.id === cohortId)?.name ?? null;
            const waiting = sitting.cohort_id
              ? trainees.filter(
                  (t) => t.cohort_id === sitting.cohort_id && !(t.user_id && onCircuit.has(t.user_id)),
                )
              : [];
            if ((data.candidates ?? []).length === 0 && waiting.length === 0) {
              return (
                <B2CHero eyebrow="Candidates" title="No candidates yet">
                  Add a circuit to put people on this sitting.
                </B2CHero>
              );
            }
            return (
              <B2CGroupedSection eyebrow="Candidates">
                {(data.candidates ?? []).map((candidate) => {
                  const label = candidate.name ?? candidate.email ?? "Candidate";
                  const trainee = byUser.get(candidate.user_id);
                  const circuits = [...new Set((candidate.stations ?? []).map((station) => station.circuit_name))];
                  return (
                    <CandidateRow
                      key={candidate.user_id}
                      label={label}
                      detail={[yearOf(trainee?.cohort_id), trainee?.invitation_pending ? "invited, not accepted" : "signed in"]
                        .filter(Boolean)
                        .join(" · ")}
                      resend={trainee?.invitation_pending ? () => void resend(trainee.id) : null}
                      note={trainee ? sent[trainee.id] : undefined}
                      circuits={circuits.join(", ")}
                    />
                  );
                })}
                {waiting.map((trainee) => (
                  <CandidateRow
                    key={trainee.id}
                    label={[trainee.first_name, trainee.last_name].filter(Boolean).join(" ") || trainee.email}
                    detail={[yearOf(trainee.cohort_id), trainee.invitation_pending ? "invited, not accepted" : "signed in"]
                      .filter(Boolean)
                      .join(" · ")}
                    resend={trainee.invitation_pending ? () => void resend(trainee.id) : null}
                    note={sent[trainee.id]}
                    circuits="Not on a circuit yet"
                  />
                ))}
              </B2CGroupedSection>
            );
          }}
        </AsyncBoundary>
      )}
    </AsyncBoundary>
  );
}

function CandidateRow({
  label,
  detail,
  resend,
  note,
  circuits,
}: {
  label: string;
  detail: string;
  resend: (() => void) | null;
  note?: string;
  circuits: string;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 text-sm">
      <span
        aria-hidden
        className="flex h-8 w-8 items-center justify-center rounded-full bg-canvas text-osce-meta font-medium text-ink"
      >
        {initials(label)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-ink">{label}</span>
        <span className="block truncate text-ink-muted">
          {detail}
          {resend ? (
            <>
              {" · "}
              <button type="button" className="text-accent underline" onClick={resend}>
                Resend invitation
              </button>
            </>
          ) : null}
          {note ? ` · ${note}` : null}
        </span>
      </span>
      <span className="text-ink-muted">{circuits}</span>
    </div>
  );
}

/** How far marking and release have got, with the way into the full results. */
function ResultsTab({ report, href }: { report: AsyncState<SittingReport>; href: string }) {
  return (
    <AsyncBoundary state={report}>
      {(data) => {
        const counts = countsFromReport(data);
        return (
          <B2CGroupedSection eyebrow="Results so far">
            <p className="px-4 py-3 text-sm text-ink">
              Stations marked {counts.stationsMarked} of {counts.stations}
            </p>
            <p className="px-4 py-3 text-sm text-ink">
              Decided {counts.decided} of {counts.candidates}
            </p>
            <p className="px-4 py-3 text-sm text-ink">
              Released {counts.released} of {counts.candidates}
            </p>
            <div className="px-4 py-3">
              <OpenResults href={href} />
            </div>
          </B2CGroupedSection>
        );
      }}
    </AsyncBoundary>
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

/** Where the sitting is in its steps, and the one action that moves it on. A cancelled sitting has none. */
function SittingNextStep({
  sitting,
  report,
  can,
  actions,
}: {
  sitting: Sitting;
  report: AsyncState<SittingReport>;
  can: SittingStepsInput["can"];
  actions: Partial<Record<SittingNextId, ReactNode>>;
}) {
  if (sitting.status === "cancelled") return null;
  return (
    <AsyncBoundary state={report}>
      {(data) => {
        const input: SittingStepsInput = {
          scheduledFor: sitting.scheduled_for,
          circuits: sitting.circuits ?? [],
          counts: countsFromReport(data),
          training: sitting.mode !== "exam",
          can,
        };
        const next = sittingNext(input);
        return (
          <StepGuide steps={sittingSteps(input)} line={next.line}>
            {next.actionable ? actions[next.id] : null}
          </StepGuide>
        );
      }}
    </AsyncBoundary>
  );
}

function OpenResults({ href }: { href: string }) {
  return (
    <ButtonLink themeType="b2b" size="sm" variant="commit" href={href}>
      Open results
    </ButtonLink>
  );
}
