"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { AsyncBoundary, b2bTokens as t } from "@/foundation/ui";
import { useAsync, type AsyncState } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import {
  listActiveTrainees,
  readSitting,
  type Circuit,
  type Sitting,
} from "@/domains/assess/api";
import {
  SittingActionDialog,
  type PendingSittingAction,
} from "@/domains/assess/SittingActions";
import { PendingCircuitsNotice } from "@/domains/assess/PendingCircuitsNotice";
import { SittingEditForm } from "@/domains/assess/SittingEditForm";
import {
  readSittingReport,
  type SittingReport,
} from "@/domains/assess/results/api";
import { readAllCohorts, resendInvitation } from "@/domains/assess/roster/api";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { boardCard, boardPad, boardRow, boardTab, boardTabs, boardChip, boardAvatar, boardBtn, boardButtonSmall } from "@/foundation/ui/boardKit";
import { sittingChipTone, sittingWhenAt } from "@/domains/assess/sittingWords";
import {
  circuitToOpen,
  countsFromReport,
  sittingNext,
  sittingSteps,
  type SittingNextId,
  type SittingStepsInput,
} from "@/domains/assess/sittingSteps";
import { sittingStatusLabel } from "@/domains/assess/support";
import { plural } from "@/foundation/format";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { boardRailStep } from "@/domains/assess/chrome";

/** One sitting and its circuits, with the way into each console. */
export function SittingDetail({
  orgSlug,
  sittingId,
}: {
  orgSlug: string;
  sittingId: string;
}) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const userId = session?.user.id ?? null;
  const state = useAsync(
    (signal) => readSitting(orgSlug, sittingId, signal),
    [orgSlug, sittingId],
  );
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState<PendingSittingAction>(null);
  const [tab, setTab] = useState<SittingTab>("circuits");
  const cohorts = useAsync(
    (signal) => readAllCohorts(orgSlug, signal),
    [orgSlug],
  );
  // The report's counts feed the steps. Every staff role reads it; a failure shows as one,
  // never as "0 marked, 0 decided".
  const report = useAsync(
    (signal) => readSittingReport(orgSlug, sittingId, signal),
    [orgSlug, sittingId],
  );

  return (
    <section aria-label="Sitting" className={t.assessPage}>
      <AsyncBoundary state={state}>
        {(sitting) => {
          const runCircuit = circuitToOpen(sitting.circuits ?? []);
          // The same permission as the cancel and delete routes (OrgAdmin). A cancelled
          // sitting takes no more changes, so its controls go with it.
          const manage =
            can(session, "schedule_sittings") && sitting.status !== "cancelled";
          const begun = (sitting.circuits ?? []).some(
            (circuit) => circuit.started_at,
          );
          const stepCan = {
            schedule: manage,
            signOff: can(session, "sign_off_results"),
          };
          const input = report.data
            ? stepsInput(sitting, report.data, stepCan)
            : null;
          const nextStep = input ? sittingNext(input) : null;
          const actions: Partial<Record<SittingNextId, ReactNode>> = {
            schedule: (
              <button
                type="button"
                className={PRIMARY}
                onClick={() => setEditing(true)}
              >
                Set a date
              </button>
            ),
            circuits: (
              <Link
                className={PRIMARY}
                href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}
              >
                Add a circuit
              </Link>
            ),
            run: runCircuit ? (
              <Link
                className={PRIMARY}
                href={hrefFor(`/circuits/${runCircuit.id}`)}
              >
                Open the console
              </Link>
            ) : null,
            mark: (
              <OpenResults href={hrefFor(`/sittings/${sitting.id}/results`)} />
            ),
            decide: (
              <OpenResults href={hrefFor(`/sittings/${sitting.id}/results`)} />
            ),
            release: (
              <OpenResults href={hrefFor(`/sittings/${sitting.id}/results`)} />
            ),
          };
          const headAction =
            nextStep?.actionable && sitting.status !== "cancelled"
              ? actions[nextStep.id]
              : null;
          return (
            <>
              <PendingCircuitsNotice
                orgSlug={orgSlug}
                sittingId={sitting.id}
                onDone={state.reload}
              />
              <div>
                <Link
                  href={hrefFor("/sittings")}
                  className="text-assess-label text-osce-accent"
                >
                  {`‹ ${w.Sittings}`}
                </Link>
              </div>
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <div className={t.assessEyebrow}>
                    {sitting.mode === "exam" ? "Formal exam" : "Training"}
                  </div>
                  <h1 className={t.assessTitle}>{sitting.name}</h1>
                  <p className={t.assessDesc}>
                    {[
                      sitting.scheduled_for
                        ? sittingWhenAt(sitting.scheduled_for)
                        : "No date set",
                      sitting.programme_name,
                      sitting.cohort_id
                        ? `Year group: ${cohorts.data?.find((cohort) => cohort.id === sitting.cohort_id)?.name ?? "…"}`
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2.5">
                  <span
                    className={boardChip(
                      sittingChipTone(sitting.status, false),
                    )}
                  >
                    {sittingStatusLabel(sitting.status, sitting.scheduled_for)}
                  </span>
                  {manage ? (
                    <button
                      type="button"
                      className={SECONDARY}
                      onClick={() => setEditing(true)}
                    >
                      Edit
                    </button>
                  ) : null}
                  {manage && !begun ? (
                    <button
                      type="button"
                      className={boardBtn("danger")}
                      onClick={() => setPending({ kind: "cancel" })}
                    >
                      Cancel sitting
                    </button>
                  ) : null}
                  <Link
                    className={SECONDARY}
                    href={hrefFor(`/sittings/${sitting.id}/results`)}
                  >
                    Results
                  </Link>
                  {headAction}
                </div>
              </div>

              <SittingNextStep
                input={input}
                report={report}
                cancelled={sitting.status === "cancelled"}
              />

              {editing ? (
                <SittingEditForm
                  orgSlug={orgSlug}
                  sitting={sitting}
                  onClose={() => setEditing(false)}
                  onSaved={state.reload}
                />
              ) : null}

              <div
                role="tablist"
                aria-label="Sitting sections"
                className={boardTabs}
              >
                {(
                  [
                    ["circuits", "Circuits"],
                    ["candidates", "Candidates"],
                    ["results", "Results so far"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={tab === key}
                    className={boardTab(tab === key)}
                    onClick={() => setTab(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {tab === "candidates" ? (
                <CandidatesTab
                  orgSlug={orgSlug}
                  sitting={sitting}
                  report={report}
                />
              ) : null}
              {tab === "results" ? (
                <ResultsTab
                  report={report}
                  href={hrefFor(`/sittings/${sitting.id}/results`)}
                />
              ) : null}
              {tab !== "circuits" ? null : (sitting.circuits ?? []).length ===
                0 ? (
                <div className={boardPad}>
                  <h2 className="text-base font-semibold leading-normal">
                    No circuits yet
                  </h2>
                  <p className={`m-0 ${t.assessMeta}`}>
                    Add at least one circuit so candidates can take this
                    sitting.
                  </p>
                </div>
              ) : (
                <div className={`${boardCard} overflow-hidden`}>
                  <div className={`${boardRow} justify-between border-t-0`}>
                    <h2 className="text-base font-semibold leading-normal">
                      Circuits
                    </h2>
                    {manage ? (
                      <Link
                        className={SMALL}
                        href={hrefFor(`/sittings/${sitting.id}/circuits/new`)}
                      >
                        Add a circuit
                      </Link>
                    ) : null}
                  </div>
                  {orderedCircuits(sitting, manage ? null : userId).map(
                    (circuit) => {
                      const mine =
                        userId !== null &&
                        circuit.supervisor_user_id === userId;
                      const stations = new Set(
                        (circuit.slots ?? []).map(
                          (slot) => slot.station_version_id,
                        ),
                      ).size;
                      return (
                        <div key={circuit.id} className={boardRow}>
                          <Link
                            href={hrefFor(`/circuits/${circuit.id}`)}
                            className="flex-[1_1_280px] text-osce-ink-900"
                          >
                            <div className="font-medium">{circuit.name}</div>
                            <div className={t.assessMeta}>
                              {[
                                circuitState(circuit),
                                ...(stations > 0
                                  ? [plural(stations, "station")]
                                  : []),
                                circuit.supervisor_user_id
                                  ? `Supervisor ${circuit.supervisor_name ?? "another supervisor"}`
                                  : "No supervisor assigned",
                              ].join(" · ")}
                            </div>
                          </Link>
                          {mine ? (
                            <span className={boardChip("info")}>
                              Your circuit
                            </span>
                          ) : circuit.started_at && !circuit.ended_at ? (
                            <span className={boardChip("live")}>Running</span>
                          ) : !circuit.started_at &&
                            circuit.supervisor_user_id &&
                            circuit.trainee_count > 0 ? (
                            <span className={boardChip("info")}>Ready</span>
                          ) : null}
                          {manage && !circuit.started_at ? (
                            <>
                              <Link
                                className={SMALL}
                                href={hrefFor(`/circuits/${circuit.id}/edit`)}
                              >
                                Edit
                              </Link>
                              <button
                                type="button"
                                className={boardBtn("danger", true)}
                                onClick={() =>
                                  setPending({ kind: "delete", circuit })
                                }
                              >
                                Delete
                              </button>
                            </>
                          ) : null}
                        </div>
                      );
                    },
                  )}
                  {(sitting.circuits ?? []).length > 1 ? (
                    <div className={boardRow}>
                      {(sitting.circuits ?? []).length - 1} more circuits ·
                      supervisors see their own circuit first
                    </div>
                  ) : null}
                </div>
              )}

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
    </section>
  );
}

const PRIMARY = boardBtn("primary");
const SECONDARY = boardBtn();
const SMALL = boardButtonSmall;

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
      setSent((current) => ({
        ...current,
        [traineeId]: assessErrorMessage(cause),
      }));
    }
  };
  return (
    <AsyncBoundary state={roster}>
      {({ trainees, cohorts }) => (
        <AsyncBoundary state={report}>
          {(data) => {
            const byUser = new Map(
              trainees
                .filter((t) => t.user_id)
                .map((t) => [t.user_id as string, t]),
            );
            const onCircuit = new Set(
              (data.candidates ?? []).map((candidate) => candidate.user_id),
            );
            const yearOf = (cohortId: string | null | undefined) =>
              cohorts.find((cohort) => cohort.id === cohortId)?.name ?? null;
            const waiting = sitting.cohort_id
              ? trainees.filter(
                  (t) =>
                    t.cohort_id === sitting.cohort_id &&
                    !(t.user_id && onCircuit.has(t.user_id)),
                )
              : [];
            if ((data.candidates ?? []).length === 0 && waiting.length === 0) {
              return (
                <div className={boardPad}>
                  <h2 className="text-base font-semibold leading-normal">
                    No candidates yet
                  </h2>
                  <p className={`m-0 ${t.assessMeta}`}>
                    Add a circuit to put people on this sitting.
                  </p>
                </div>
              );
            }
            return (
              <div className={`${boardCard} overflow-hidden`}>
                <div className={`${boardRow} border-t-0`}>
                  <h2 className="text-base font-semibold leading-normal">
                    Candidates
                  </h2>
                </div>
                {(data.candidates ?? []).map((candidate) => {
                  const label =
                    candidate.name ?? candidate.email ?? "Candidate";
                  const trainee = byUser.get(candidate.user_id);
                  const circuits = [
                    ...new Set(
                      (candidate.stations ?? []).map(
                        (station) => station.circuit_name,
                      ),
                    ),
                  ];
                  return (
                    <CandidateRow
                      key={candidate.user_id}
                      label={label}
                      detail={[
                        yearOf(trainee?.cohort_id),
                        trainee?.invitation_pending
                          ? "invited, not accepted"
                          : "signed in",
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                      resend={
                        trainee?.invitation_pending
                          ? () => void resend(trainee.id)
                          : null
                      }
                      note={trainee ? sent[trainee.id] : undefined}
                      circuits={circuits.join(", ")}
                    />
                  );
                })}
                {waiting.map((trainee) => (
                  <CandidateRow
                    key={trainee.id}
                    label={
                      [trainee.first_name, trainee.last_name]
                        .filter(Boolean)
                        .join(" ") || trainee.email
                    }
                    detail={[
                      yearOf(trainee.cohort_id),
                      trainee.invitation_pending
                        ? "invited, not accepted"
                        : "signed in",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                    resend={
                      trainee.invitation_pending
                        ? () => void resend(trainee.id)
                        : null
                    }
                    note={sent[trainee.id]}
                    circuits="Not on a circuit yet"
                  />
                ))}
              </div>
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
    <div className={boardRow}>
      <span aria-hidden className={boardAvatar}>
        {initials(label)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{label}</span>
        <span className={`block truncate ${t.assessMeta}`}>
          {detail}
          {resend ? (
            <>
              {" · "}
              <button
                type="button"
                className="text-osce-accent"
                onClick={resend}
              >
                Resend invitation
              </button>
            </>
          ) : null}
          {note ? ` · ${note}` : null}
        </span>
      </span>
      <span className={t.assessMeta}>{circuits}</span>
    </div>
  );
}

/** How far marking and release have got, with the way into the full results. */
function ResultsTab({
  report,
  href,
}: {
  report: AsyncState<SittingReport>;
  href: string;
}) {
  return (
    <AsyncBoundary state={report}>
      {(data) => {
        const counts = countsFromReport(data);
        return (
          <div className="flex flex-col gap-3.5">
            <div className="grid grid-cols-1 gap-3 min-[900px]:grid-cols-3">
              {(
                [
                  [
                    "Stations marked",
                    `${counts.stationsMarked} of ${counts.stations}`,
                  ],
                  ["Decided", `${counts.decided} of ${counts.candidates}`],
                  ["Released", `${counts.released} of ${counts.candidates}`],
                ] as const
              ).map(([label, value]) => (
                <div
                  key={label}
                  className={`${boardCard} p-4 text-assess-label`}
                >
                  {label}
                  <b className="mt-1 block text-assess-num font-semibold">
                    {value}
                  </b>
                </div>
              ))}
            </div>
            <Link className={`${SECONDARY} self-start`} href={href}>
              Open results
            </Link>
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

/** A supervisor's own circuits first, then the rest in the server's order; an administrator sees the server's order. */
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
  if (circuit.started_at)
    return `Running since ${new Date(circuit.started_at).toLocaleTimeString()}`;
  return "Not started";
}

/** Where the sitting is in its steps, and the one action that moves it on. A cancelled sitting has none. */
/** What the steps and the next line are worked out from. */
function stepsInput(
  sitting: Sitting,
  data: SittingReport,
  can: SittingStepsInput["can"],
): SittingStepsInput {
  return {
    scheduledFor: sitting.scheduled_for,
    circuits: sitting.circuits ?? [],
    counts: countsFromReport(data),
    training: sitting.mode !== "exam",
    can,
  };
}

/** The step rail and the line under it; the step's own action is the head's primary button. */
function SittingNextStep({
  input,
  report,
  cancelled,
}: {
  input: SittingStepsInput | null;
  report: AsyncState<SittingReport>;
  cancelled: boolean;
}) {
  if (cancelled) return null;
  return (
    <AsyncBoundary state={report}>
      {() => {
        if (!input) return null;
        const steps = sittingSteps(input);
        const nowId = steps.find((step) => step.state !== "done")?.id;
        return (
          <div className={boardPad}>
            <ol aria-label="Steps" className="flex flex-wrap gap-2">
              {steps.map((step) => (
                <li
                  key={step.id}
                  className={boardRailStep(step.state, step.id === nowId)}
                >
                  <b className="block text-assess-label font-medium">
                    {step.label}
                  </b>
                  {step.note}
                </li>
              ))}
            </ol>
            <div className="text-assess-label">{sittingNext(input).line}</div>
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

function OpenResults({ href }: { href: string }) {
  return (
    <Link className={PRIMARY} href={href}>
      Open results
    </Link>
  );
}
