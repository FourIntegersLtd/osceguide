"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  AsyncBoundary,
  B2CPageHeader,
  Button,
  ButtonLink,
  Input,
  Panel,
  Spinner,
  StepRail,
  type RailStep,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import {
  createSitting,
  listActiveMembers,
  listActiveTrainees,
  listProgrammes,
  type Programme,
  type SittingMode,
} from "@/domains/assess/api";
import {
  readAllCohorts,
  readAllTraineeGroups,
  readGroupMembers,
} from "@/domains/assess/roster/api";
import { FieldSelect } from "@/domains/assess/SittingFields";
import {
  CandidatePicker,
  StationOrder,
  SummaryRows,
  SupervisorStep,
  TimingStep,
} from "@/domains/assess/ScheduleSteps";
import {
  EMPTY_DRAFT,
  examTimings,
  SCHEDULE_STEPS,
  STEP_HELP,
  candidateNames,
  furthestStep,
  peopleFormula,
  scheduledInstant,
  stepBlock,
  stepUnlocked,
  timingSummary,
  type ScheduleDraft,
  type ScheduleStepId,
  type PickerSet,
  type TraineeRow,
} from "@/domains/assess/scheduleSitting";
import { circuitLeads } from "@/domains/assess/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { circuitsMade, createSittingCircuits, savePending } from "@/domains/assess/scheduleCircuits";

/**
 * Schedule a sitting in six steps that unlock in order.
 *
 * Nothing is created until the last step. Then the sitting is made and its
 * circuits follow; if the circuits fail the sitting exists, so the screen keeps
 * its id and "Try again" re-runs only the circuits instead of making a second
 * sitting.
 */
export function NewSitting({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const [programmes, trainees, staff, groupPage, cohortPage] = await Promise.all([
        listProgrammes(orgSlug, signal),
        listActiveTrainees(orgSlug, signal),
        listActiveMembers(orgSlug, signal),
        readAllTraineeGroups(orgSlug, signal),
        readAllCohorts(orgSlug, signal),
      ]);
      const groups: PickerSet[] = groupPage.map((group) => ({
        id: group.id,
        label: group.label,
        count: group.member_count,
        loadMemberIds: () => readGroupMembers(orgSlug, group.id, signal),
      }));
      // The api has no cohort filter, so a year group's members are the loaded trainees tagged with it.
      const yearGroups: PickerSet[] = cohortPage.map((cohort) => ({
        id: cohort.id,
        label: cohort.name,
        count: trainees.filter((t) => t.cohort_id === cohort.id).length,
        loadMemberIds: async () => trainees.filter((t) => t.cohort_id === cohort.id).map((t) => t.id),
      }));
      return {
        programmes: programmes.items,
        trainees,
        groups,
        yearGroups,
        cohorts: cohortPage,
        leads: circuitLeads(staff).map((member) => ({
          value: member.user_id,
          label: `${member.email ?? member.user_id} (${member.role})`,
        })),
      };
    },
    [orgSlug],
  );

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        back={{ href: hrefFor("/sittings"), label: w.Sittings }}
        title={w.scheduleSitting}
        subtitle="Steps unlock in order. Nothing is created until the last step."
      />
      <AsyncBoundary state={context}>
        {(data) => (
          <Wizard
            orgSlug={orgSlug}
            programmes={data.programmes}
            trainees={data.trainees}
            groups={data.groups}
            yearGroups={data.yearGroups}
            cohorts={data.cohorts}
            leads={data.leads}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Wizard({
  orgSlug,
  programmes,
  trainees,
  groups,
  yearGroups,
  cohorts,
  leads: allLeads,
}: {
  orgSlug: string;
  programmes: Programme[];
  trainees: TraineeRow[];
  groups: PickerSet[];
  yearGroups: PickerSet[];
  cohorts: { id: string; name: string }[];
  leads: { value: string; label: string }[];
}) {
  const w = useAssessWords();
  const router = useRouter();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  // The signed-in person is marked "(you)" in every supervisor list.
  const leads = allLeads.map((lead) =>
    lead.value === session?.user.id ? { ...lead, label: `${lead.label} (you)` } : lead,
  );
  const ready = useMemo(() => programmes.filter((programme) => programme.status === "active"), [programmes]);

  const [draft, setDraft] = useState<ScheduleDraft>({
    ...EMPTY_DRAFT,
    programmeId: ready[0]?.id ?? "",
    ...(ready[0] ? examTimings(ready[0]) : {}),
  });
  const [step, setStep] = useState<ScheduleStepId>("basics");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patch = useCallback((change: Partial<ScheduleDraft>) => setDraft((current) => ({ ...current, ...change })), []);
  const programme = ready.find((item) => item.id === draft.programmeId);
  const scope = useMemo(
    () => ({ orgSlug, examCode: programme?.exam_code ?? null, orgOwnedExam: programme?.exam_owner_kind === "org" }),
    [orgSlug, programme],
  );
  const furthest = furthestStep(draft);
  const index = SCHEDULE_STEPS.findIndex((item) => item.id === step);
  const block = stepBlock(step, draft);
  const names = useMemo(() => candidateNames(trainees), [trainees]);

  if (ready.length === 0) {
    const drafts = programmes.filter((item) => item.status === "draft").map((item) => item.exam_name);
    return (
      <Alert tone="warning" title="No exam is ready to schedule">
        <p>
          {drafts.length > 0
            ? `${drafts.join(", ")} ${drafts.length === 1 ? "is" : "are"} still a draft. Finish setting it up, then come back here.`
            : `Every ${w.sitting} belongs to an exam with a published marking scheme. Set one up, then come back here.`}
        </p>
        <ButtonLink href={hrefFor("/programmes")} themeType="b2b" variant="secondary" className="mt-2">
          Set up an exam
        </ButtonLink>
      </Alert>
    );
  }

  const railSteps: RailStep<ScheduleStepId>[] = SCHEDULE_STEPS.map((item, at) => ({
    id: item.id,
    label: item.label,
    state: at < SCHEDULE_STEPS.findIndex((s) => s.id === furthest) ? "done" : "todo",
    note: item.title,
  }));

  const create = async () => {
    setBusy(true);
    setError(null);
    let sittingId: string;
    try {
      const sitting = await createSitting(orgSlug, {
        name: draft.name.trim(),
        mode: draft.mode,
        programmeId: draft.programmeId,
        cohortId: draft.cohortId || null,
        scheduledFor: scheduledInstant(draft),
      });
      sittingId = sitting.id;
    } catch (cause) {
      setError(assessErrorMessage(cause));
      setBusy(false);
      return;
    }
    try {
      await createSittingCircuits(orgSlug, sittingId, draft, 0);
    } catch (cause) {
      // The sitting exists: land on it with the error and a "Try again" that makes the circuits.
      savePending(sittingId, { draft, created: circuitsMade(cause), message: assessErrorMessage(cause) });
    }
    router.push(hrefFor(`/sittings/${sittingId}`));
  };

  const formula = peopleFormula(draft, { trainee: w.trainee, trainees: w.trainees });
  const kindLabel = draft.mode === "exam" ? "Formal exam" : "Training";
  const year = cohorts.find((cohort) => cohort.id === draft.cohortId)?.name ?? "None";
  const leadLabel = (id: string) => leads.find((lead) => lead.value === id)?.label ?? "Unassigned";

  return (
    <div className="flex max-w-5xl flex-col gap-5">
      <StepRail
        steps={railSteps}
        current={step}
        onSelect={(id) => stepUnlocked(id, draft) && setStep(id)}
      />
      <p className="text-sm text-ink-muted">
        Step {index + 1} of {SCHEDULE_STEPS.length}
      </p>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
      <Panel title={SCHEDULE_STEPS[index]?.title}>
        {step === "basics" ? (
          <div className="flex max-w-lg flex-col gap-4">
            <p className="text-sm text-ink-muted">
              What this {w.sitting} is, which exam it uses and when it happens.
            </p>
            <Input
              label="Name"
              value={draft.name}
              onChange={(event) => patch({ name: event.target.value })}
              placeholder="Summer finals"
            />
            <FieldSelect
              label="Exam"
              value={draft.programmeId}
              onChange={(value) => {
                const chosen = ready.find((item) => item.id === value);
                patch({
                  programmeId: value,
                  stations: [],
                  readingMinutes: EMPTY_DRAFT.readingMinutes,
                  consultationMinutes: EMPTY_DRAFT.consultationMinutes,
                  breakMinutes: EMPTY_DRAFT.breakMinutes,
                  ...(chosen ? examTimings(chosen) : {}),
                });
              }}
              options={ready.map((item) => ({ value: item.id, label: `${item.exam_name} · Ready to schedule` }))}
            />
            <p className="text-sm text-ink-muted">
              Only exams that are ready to schedule show here. Missing one?{" "}
              <ButtonLink href={hrefFor("/programmes")} themeType="b2b" variant="ghost">
                Set up an exam
              </ButtonLink>
            </p>
            <fieldset className="flex flex-col gap-1.5">
              <legend className="text-sm font-medium text-ink">Kind</legend>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {(
                  [
                    ["exam", "Formal exam", "Marked, signed off and released"],
                    ["training", "Training", "Feedback straight to the trainee"],
                  ] as [SittingMode, string, string][]
                ).map(([value, title, body]) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={draft.mode === value}
                    onClick={() => patch({ mode: value })}
                    className={`flex flex-col items-start gap-0.5 rounded-control border px-4 py-3 text-left ${
                      draft.mode === value ? "border-b2b-headline bg-canvas" : "border-b2b-border bg-b2b-surface hover:bg-canvas"
                    }`}
                  >
                    <span className="text-osce-body font-medium text-b2b-headline">{title}</span>
                    <span className="text-osce-meta text-b2b-mid">{body}</span>
                  </button>
                ))}
              </div>
            </fieldset>
            <Input
              label="Date"
              type="date"
              value={draft.date}
              hint="You can leave it blank and set it later."
              onChange={(event) => patch({ date: event.target.value })}
            />
            <FieldSelect
              label="Year group"
              value={draft.cohortId}
              onChange={(value) => patch({ cohortId: value })}
              options={[{ value: "", label: "None" }, ...cohorts.map((c) => ({ value: c.id, label: c.name }))]}
            />
          </div>
        ) : null}

        {step === "stations" ? (
          <StationOrder
            stations={draft.stations}
            setStations={(update) => setDraft((current) => ({ ...current, stations: update(current.stations) }))}
            scope={scope}
            examName={programme?.exam_name ?? "this exam"}
            heading={`Published stations from ${programme?.exam_name ?? "this exam"}. Drag to set the order every candidate goes round.${
              draft.mode === "exam" ? " At most 12 on a formal exam circuit." : ""
            }`}
          />
        ) : null}

        {step === "people" ? (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink-muted">Pick people one by one, or add a whole group or year group.</p>
            <CandidatePicker
              orgSlug={orgSlug}
              trainees={trainees}
              picked={draft.candidateIds}
              setPicked={(update) => setDraft((current) => ({ ...current, candidateIds: update(current.candidateIds) }))}
              groups={groups}
              yearGroups={yearGroups}
              single={draft.mode === "exam"}
              words={{ trainee: w.trainee, trainees: w.trainees }}
            />
            <p role="status" className={`text-sm ${formula.ok ? "text-ink-muted" : "text-osce-warning-text"}`}>
              {formula.formula} {formula.help}
            </p>
          </div>
        ) : null}

        {step === "timing" ? <TimingStep draft={draft} patch={patch} /> : null}

        {step === "supervisor" ? (
          <SupervisorStep
            draft={draft}
            patch={patch}
            leads={leads}
            candidateNames={names}
            inviteHref={hrefFor("/team")}
          />
        ) : null}

        {step === "review" ? (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-ink-muted">Check it over. You can change everything on the {w.sitting} page afterwards.</p>
            <SummaryRows
              rows={[
                [w.Sitting, draft.name.trim()],
                ["Exam", programme?.exam_name ?? ""],
                ["Kind", kindLabel],
                ["Year group", year],
                ["Stations", String(draft.stations.length)],
                [w.Trainees, String(draft.candidateIds.length)],
                ["Timing", timingSummary(draft)],
                [
                  "Supervisor",
                  draft.perCandidate && draft.mode === "exam"
                    ? "One for each candidate"
                    : leadLabel(draft.supervisorId),
                ],
              ]}
            />
          </div>
        ) : null}
      </Panel>
      <aside aria-label="Help" className="h-fit rounded-control border border-border bg-surface p-4 text-sm">
        <p className="font-medium text-ink">Help</p>
        <p className="mt-2 font-medium text-ink">{STEP_HELP[step].title}</p>
        <p className="mt-1 text-ink-muted">{STEP_HELP[step].body}</p>
      </aside>
      </div>

      {block && step !== "review" ? <p className="text-sm text-ink-muted">{block}</p> : null}

      <div className="flex justify-between gap-2">
        <Button themeType="b2b" variant="secondary" disabled={index === 0 || busy} onClick={() => setStep(SCHEDULE_STEPS[index - 1]?.id ?? step)}>
          Back
        </Button>
        {step === "review" ? (
          <Button themeType="b2b" variant="commit" disabled={busy} onClick={() => void create()}>
            {busy ? <Spinner label="Creating" className="text-current" /> : `Create ${w.sitting}`}
          </Button>
        ) : (
          <Button
            themeType="b2b"
            variant="commit"
            disabled={block !== null}
            onClick={() => setStep(SCHEDULE_STEPS[index + 1]?.id ?? step)}
          >
            Continue
          </Button>
        )}
      </div>
    </div>
  );
}
