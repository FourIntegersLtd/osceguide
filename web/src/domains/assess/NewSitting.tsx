"use client";

import { boardBtn } from "@/foundation/ui/boardKit";
import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Alert,
  AsyncBoundary,
  b2bTokens as t,
  Button,
  ButtonLink,
  cn,
  Spinner,
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
} from "@/domains/assess/api";
import {
  readAllCohorts,
  readAllTraineeGroups,
  readGroupMembers,
} from "@/domains/assess/roster/api";
import {
  Field,
  FieldSelect,
  Note,
  OptionCards,
  fieldInput,
} from "@/domains/assess/SittingFields";
import {
  linkClass,
  CandidatePicker,
  ReviewFormula,
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
  scheduleWords,
  candidateNames,
  peopleFormula,
  MODE_OPTIONS,
  reviewFormula,
  scheduledInstant,
  sittingLine,
  stationNote,
  stepBlock,
  stationAssessorsFor,
  stepUnlocked,
  timingSummary,
  type ScheduleDraft,
  type ScheduleStepId,
  type PickerSet,
  type TraineeRow,
} from "@/domains/assess/scheduleSitting";
import { circuitLeads } from "@/domains/assess/support";
import { assessorTally, tallyText } from "@/domains/assess/rotations";
import { NEW_EXAM_PATH } from "@/domains/assess/dashboard/setupSteps";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { SaveAsTemplate, TemplatePicker } from "@/domains/assess/SittingTemplates";
import { fromTemplateConfig, toTemplateConfig } from "@/domains/assess/templateConfig";
import {
  circuitsMade,
  createSittingCircuits,
  savePending,
} from "@/domains/assess/scheduleCircuits";

/**
 * Schedule a sitting in six steps that unlock in order.
 *
 * Nothing is created until the last step. Then the sitting is made and its
 * circuits follow; if the circuits fail the sitting exists, so the screen keeps
 * its id and "Try again" re-runs only the circuits instead of making a second
 * sitting.
 */
/** The board's button: 44px tall, 9px corners, 18px sides. */
const BOARD_BUTTON = "!h-11 min-h-11 rounded-board px-[18px]";

/** Who has how many rotations, for the review. */
function rotationLine(candidateIds: string[], byCandidate: Record<string, string>, leads: { value: string; label: string }[]): string {
  return tallyText(assessorTally(candidateIds, byCandidate, Object.fromEntries(leads.map((l) => [l.value, l.label])))) || "Nobody yet";
}

/** Hire review rows for what only a hire workspace sets: staggered starts and station assessors. */
function hireRows(
  draft: ScheduleDraft,
  leadLabel: (id: string) => string,
  w: ReturnType<typeof useAssessWords>,
): [string, string][] {
  const rows: [string, string][] = [];
  if (draft.staggerMinutes > 0 && draft.candidateIds.length > 1) {
    rows.push([`${w.Circuits} start`, `${draft.staggerMinutes} minutes apart`]);
  }
  const picked = stationAssessorsFor(draft);
  if (Object.keys(picked).length > 0) {
    rows.push([
      `${w.Supervisors} by station`,
      draft.stations
        .map((station, at) => `${at + 1}: ${leadLabel(picked[station.version_id] ?? "") || "default"}`)
        .join(" · "),
    ]);
  }
  return rows;
}

export function NewSitting({ orgSlug }: { orgSlug: string }) {
  const context = useAsync(
    async (signal) => {
      const [programmes, trainees, staff, groupPage, cohortPage] =
        await Promise.all([
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
        loadMemberIds: async () =>
          trainees.filter((t) => t.cohort_id === cohort.id).map((t) => t.id),
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
    lead.value === session?.user.id
      ? { ...lead, label: `${lead.label} (you)` }
      : lead,
  );
  const ready = useMemo(
    () => programmes.filter((programme) => programme.status === "active"),
    [programmes],
  );

  const [draft, setDraft] = useState<ScheduleDraft>({
    ...EMPTY_DRAFT,
    programmeId: ready[0]?.id ?? "",
    ...(ready[0] ? examTimings(ready[0]) : {}),
  });
  const [step, setStep] = useState<ScheduleStepId>("basics");
  const [reached, setReached] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templatesKey, setTemplatesKey] = useState(0);

  const patch = useCallback(
    (change: Partial<ScheduleDraft>) =>
      setDraft((current) => ({ ...current, ...change })),
    [],
  );
  const programme = ready.find((item) => item.id === draft.programmeId);
  const scope = useMemo(
    () => ({
      orgSlug,
      examCode: programme?.exam_code ?? null,
      orgOwnedExam: programme?.exam_owner_kind === "org",
    }),
    [orgSlug, programme],
  );
  const people = peopleFormula(draft, {
    trainee: w.trainee,
    trainees: w.trainees,
  });
  const index = SCHEDULE_STEPS.findIndex((item) => item.id === step);
  const block = stepBlock(step, draft);
  const names = useMemo(() => candidateNames(trainees), [trainees]);

  if (ready.length === 0) {
    const drafts = programmes
      .filter((item) => item.status === "draft")
      .map((item) => item.exam_name);
    return (
      <Alert tone="warning" title="No exam is ready to schedule">
        <p>
          {drafts.length > 0
            ? `${drafts.join(", ")} ${drafts.length === 1 ? "is" : "are"} still a draft. Finish setting it up, then come back here.`
            : `Every ${w.sitting} belongs to an exam with a published marking scheme. Set one up, then come back here.`}
        </p>
        <ButtonLink
          href={hrefFor(NEW_EXAM_PATH)}
          themeType="b2b"
          variant="secondary"
          className="mt-2"
        >
          Set up an exam
        </ButtonLink>
      </Alert>
    );
  }

  const go = (to: number) => {
    const target = SCHEDULE_STEPS[to];
    if (!target) return;
    setStep(target.id);
    setReached((current) => Math.max(current, to));
  };

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
      setError(assessErrorMessage(cause, w));
      setBusy(false);
      return;
    }
    try {
      await createSittingCircuits(orgSlug, sittingId, draft, 0);
    } catch (cause) {
      // The sitting exists: land on it with the error and a "Try again" that makes the circuits.
      savePending(sittingId, {
        draft,
        created: circuitsMade(cause),
        message: assessErrorMessage(cause, w),
      });
    }
    router.push(hrefFor(`/sittings/${sittingId}`));
  };

  const kindLabel =
    MODE_OPTIONS.find((option) => option.value === draft.mode)?.title ?? "";
  const year =
    cohorts.find((cohort) => cohort.id === draft.cohortId)?.name ?? "None";
  const leadLabel = (id: string) =>
    leads.find((lead) => lead.value === id)?.label ?? "Unassigned";
  const review = reviewFormula(
    draft,
    leadLabel(draft.supervisorId) === "Unassigned"
      ? ""
      : leadLabel(draft.supervisorId),
    w,
  );
  const current = SCHEDULE_STEPS[index];
  const last = index === SCHEDULE_STEPS.length - 1;
  const setStations = (
    update: (current: ScheduleDraft["stations"]) => ScheduleDraft["stations"],
  ) => setDraft((now) => ({ ...now, stations: update(now.stations) }));

  return (
    <div className="-mx-4 flex flex-col">
      <div className="flex flex-wrap items-center gap-4 border-b border-osce-border bg-osce-surface px-6 py-3.5">
        <Link
          href={hrefFor("/sittings")}
          className={cn(boardBtn(), BOARD_BUTTON)}
        >
          Close
        </Link>
        <h1 className="text-assess-label font-semibold">{w.scheduleSitting}</h1>
        <span className={t.assessMeta}>
          Steps unlock in order. Nothing is created until the last step.
        </span>
      </div>
      <div className="mx-auto w-full max-w-[1072px]">
        <nav aria-label="Steps" className="flex flex-wrap gap-1.5 px-4 pt-6">
          {SCHEDULE_STEPS.map((item, at) => {
            const open = stepUnlocked(item.id, draft);
            const done = at < reached && at !== index;
            return (
              <button
                key={item.id}
                type="button"
                disabled={!open}
                aria-current={at === index ? "step" : undefined}
                onClick={() => go(at)}
                className={cn(
                  "inline-flex min-h-11 flex-[1_1_130px] items-center gap-2 rounded-osce-md border px-2.5 py-2 text-left text-assess-meta",
                  at === index
                    ? "border-osce-border bg-osce-surface font-medium text-ink"
                    : done || open
                      ? "border-transparent text-osce-ink-700"
                      : "cursor-not-allowed border-transparent text-osce-ink-400",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "box-border flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[12px]",
                    done
                      ? "border-osce-success-solid bg-osce-success-solid text-white"
                      : at === index
                        ? "border-osce-accent bg-osce-surface text-osce-accent"
                        : "border-osce-border bg-osce-surface",
                  )}
                >
                  {done ? "✓" : at + 1}
                </span>
                {scheduleWords(item.label, w)}
              </button>
            );
          })}
        </nav>
        <div className="flex flex-wrap items-start gap-6 px-4 pb-16 pt-8">
          <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-6">
            {error ? <Alert tone="danger">{error}</Alert> : null}
            <header className="flex flex-col">
              <p className={t.assessEyebrow}>
                Step {index + 1} of {SCHEDULE_STEPS.length}
              </p>
              <h2 className={t.assessTitle}>{current ? scheduleWords(current.title, w) : null}</h2>
              <p className={t.assessDesc}>
                {step === "stations"
                  ? `Published stations from ${programme?.exam_name ?? "this exam"}. Drag to set the order every candidate goes round.`
                  : current ? scheduleWords(current.desc, w) : null}
              </p>
            </header>

            {step === "basics" ? (
              <div className={cn(t.assessCard, "p-6", t.assessFormStack)}>
                <TemplatePicker
                  orgSlug={orgSlug}
                  reloadKey={templatesKey}
                  onApply={(config) =>
                    setDraft((now) => ({ ...now, ...fromTemplateConfig(config, ready, now) }))
                  }
                />
                <Field label="Name" htmlFor="sitting-name">
                  <input
                    id="sitting-name"
                    className={fieldInput}
                    value={draft.name}
                    onChange={(event) => patch({ name: event.target.value })}
                    placeholder="Summer finals"
                  />
                </Field>
                <FieldSelect
                  label="Exam"
                  id="sitting-exam"
                  hint={
                    <>
                      Only exams that are ready to schedule show here. Missing
                      one?{" "}
                      <Link href={hrefFor(NEW_EXAM_PATH)} className={linkClass}>
                        Set up an exam
                      </Link>
                    </>
                  }
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
                  options={ready.map((item) => ({
                    value: item.id,
                    label: `${item.exam_name} · Ready to schedule`,
                  }))}
                />
                <OptionCards
                  label="Kind"
                  options={MODE_OPTIONS.map((option) => ({
                    key: option.value,
                    title: option.title,
                    body: option.body,
                    selected: draft.mode === option.value,
                    onSelect: () => patch({ mode: option.value }),
                  }))}
                />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field
                    label="Date"
                    htmlFor="sitting-date"
                    hint="You can leave it blank and set it later."
                  >
                    <input
                      id="sitting-date"
                      className={fieldInput}
                      type="date"
                      value={draft.date}
                      onChange={(event) => patch({ date: event.target.value })}
                    />
                  </Field>
                  <FieldSelect
                    label="Year group"
                    id="sitting-year"
                    value={draft.cohortId}
                    onChange={(value) => patch({ cohortId: value })}
                    options={[
                      { value: "", label: "None" },
                      ...cohorts.map((c) => ({ value: c.id, label: c.name })),
                    ]}
                  />
                </div>
              </div>
            ) : null}

            {step === "stations" ? (
              <StationOrder
                stations={draft.stations}
                setStations={setStations}
                scope={scope}
                examName={programme?.exam_name ?? "this exam"}
                note={stationNote(draft)}
              />
            ) : null}

            {step === "people" ? (
              <div className="flex flex-col gap-6">
                <CandidatePicker
                  orgSlug={orgSlug}
                  trainees={trainees}
                  picked={draft.candidateIds}
                  setPicked={(update) =>
                    setDraft((now) => ({
                      ...now,
                      candidateIds: update(now.candidateIds),
                    }))
                  }
                  groups={groups}
                  yearGroups={yearGroups}
                  single={draft.mode === "exam"}
                  words={{ trainee: w.trainee, trainees: w.trainees }}
                  showCount={false}
                />
                <Note tone={people.ok ? "ok" : "warn"}>
                  {people.formula} {people.help}
                </Note>
              </div>
            ) : null}

            {step === "timing" ? (
              <TimingStep draft={draft} patch={patch} />
            ) : null}

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
              <>
                <ReviewFormula formula={review.formula} help={review.help} />
                <SummaryRows
                  rows={[
                    [w.Sitting, sittingLine(draft)],
                    ["Exam", programme?.exam_name ?? ""],
                    ["Kind", kindLabel],
                    ["Year group", year],
                    ["Timing", timingSummary(draft)],
                    [
                      w.Supervisor,
                      draft.perCandidate && draft.mode === "exam"
                        ? rotationLine(draft.candidateIds, draft.supervisorByCandidate, leads)
                        : leadLabel(draft.supervisorId),
                    ],
                    ...(w.hiring && draft.mode === "exam" ? hireRows(draft, leadLabel, w) : []),
                  ]}
                />
                <SaveAsTemplate
                  orgSlug={orgSlug}
                  config={toTemplateConfig(draft)}
                  onSaved={() => setTemplatesKey((now) => now + 1)}
                />
                <p className={t.assessMeta}>
                  If the {w.sitting} is made but its circuits fail, you land on
                  the {w.sitting} with the error and a &quot;Try again&quot;
                  button.
                </p>
              </>
            ) : null}

            {block && step !== "review" ? (
              <p className={t.assessMeta}>{block}</p>
            ) : null}

            <div className={t.assessFooter}>
              {index === 0 ? (
                <Link
                  href={hrefFor("/sittings")}
                  className={cn(boardBtn(), BOARD_BUTTON)}
                >
                  Back
                </Link>
              ) : (
                <Button
                  themeType="b2b"
                  variant="secondary"
                  className={BOARD_BUTTON}
                  disabled={busy}
                  onClick={() => go(index - 1)}
                >
                  Back
                </Button>
              )}
              {last ? (
                <Button
                  themeType="b2b"
                  variant="commit"
                  className={BOARD_BUTTON}
                  disabled={busy}
                  onClick={() => void create()}
                >
                  {busy ? (
                    <Spinner label="Creating" className="text-current" />
                  ) : (
                    `Create ${w.sitting}`
                  )}
                </Button>
              ) : (
                <Button
                  themeType="b2b"
                  variant="commit"
                  className={BOARD_BUTTON}
                  disabled={block !== null}
                  onClick={() => go(index + 1)}
                >
                  Continue
                </Button>
              )}
            </div>
          </div>
          <aside
            aria-label="Help"
            className={cn(t.assessCard, "h-fit flex-[1_1_302px] p-5")}
          >
            <p className={t.assessEyebrow}>Help</p>
            <p className="mt-2 font-medium text-ink">{scheduleWords(STEP_HELP[step].title, w)}</p>
            <p className={cn(t.assessMeta, "mt-1")}>{scheduleWords(STEP_HELP[step].body, w)}</p>
          </aside>
        </div>
      </div>
    </div>
  );
}
