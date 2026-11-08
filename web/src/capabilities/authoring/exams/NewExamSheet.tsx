"use client";

import { useAssessWords, type AssessWords } from "@/capabilities/assess-words";
import { newExamNameLead, newExamTimingsLead, schemeWayTitle, startFromOurs } from "@/capabilities/authoring/lib/authoringCopy";
import type { ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Alert,
  AsyncBoundary,
  b2bTokens as t,
  B2CPageHeader,
  Select,
  cn,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { Exam, Programme } from "@/capabilities/authoring/api";
import { BoardChip } from "@/capabilities/authoring/parts/boardUi";
import { boardCardClipped, boardBtn, boardInput } from "@/foundation/ui/boardKit";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import Link from "next/link";
import { examNewPath, examsListPath } from "@/capabilities/authoring/exams/paths";
import {
  NEW_EXAM_STEPS,
  MAX_CONSULT_MIN,
  MAX_READING_MIN,
  PUBLISH_STEP_WORDS,
  timingsLine,
  MAX_BREAK_MIN,
} from "@/capabilities/authoring/exams/newExam";
import { useNewExam, type SchemeWay } from "@/capabilities/authoring/exams/useNewExam";
import { useExam } from "@/capabilities/authoring/exams/useExam";
import { useSchemeVersions } from "@/capabilities/authoring/sections/ExamFields";
import { ExamSettingsFields } from "@/capabilities/authoring/sections/ExamSettingsFields";
import { examQuery, rubricNewPath } from "@/capabilities/authoring/templates/paths";

const SCHEME_WAYS: { id: SchemeWay; title: string; body?: string }[] = [
  { id: "use", title: "Use one of your marking schemes" },
  { id: "copy", title: "Copy one from OSCE Guide", body: "Start from a tested scheme and change what you need." },
  { id: "write", title: "Write a new marking scheme", body: "Name the domains, the ratings and what each means." },
];

/** "New exam": one sheet that makes the exam, picks its marking scheme, sets timings, then publishes and offers it. */
export function NewExamSheet() {
  const examId = useSearchParams().get("exam");
  return (
    <RequireAuthor>
      {/* No exam id: the sheet starts at the Name step. AsyncBoundary renders nothing for a null result. */}
      {examId ? <ResumedSheet examId={examId} /> : <Sheet first={null} firstProgramme={null} />}
    </RequireAuthor>
  );
}

/** A saved draft is read back so the sheet resumes where it stopped. */
function ResumedSheet({ examId }: { examId: string }) {
  const saved = useExam(examId);
  const { hrefFor } = useSurface();
  return (
    <AsyncBoundary
      state={saved}
      empty={{
        title: "That exam was not found",
        description: "It may have been deleted, or it belongs to another organisation.",
        action: <Link href={examNewPath(hrefFor)} className="text-osce-body font-medium text-accent underline">Start a new exam</Link>,
      }}
    >
      {(found) => <Sheet key={found?.exam.id ?? "new"} first={found?.exam ?? null} firstProgramme={found?.programme ?? null} />}
    </AsyncBoundary>
  );
}

function Sheet({ first, firstProgramme }: { first: Exam | null; firstProgramme: Programme | null }) {
  const w = useAssessWords();
  const HEADINGS = headings(w);
  const ours = startFromOurs(w);
  const { hrefFor } = useSurface();
  const router = useRouter();
  const sheet = useNewExam(first, firstProgramme);
  const { draft, setDraft, step, busy, error, failedStep, minutes, timings, nameProblem, exam, way } = sheet;
  const { rubrics, versions } = useSchemeVersions(draft.rubricVersionId);
  const schemeLabel = versions.find((v) => v.id === draft.rubricVersionId)?.label ?? "None chosen";

  const setBreak = (value: string) =>
    setDraft({
      ...draft,
      settings: { ...draft.settings, default_break_minutes: value.trim() === "" ? null : Number(value) },
    });
  const setMinutes = (field: "reading" | "simulation", value: string) =>
    setDraft({ ...draft, [field]: String(Math.round(Number(value) * 60)) });

  return (
    <div className="flex flex-col gap-8 pb-8">
      <B2CPageHeader
        eyebrow="Your progress is saved after each step"
        title="New exam"
        back={{ href: examsListPath(hrefFor), label: "Close" }}
      />
      <div data-testid="new-exam-body" className="-mx-6 flex w-[calc(100%+3rem)] max-w-[792px] flex-col gap-6 self-start px-6 pb-16 pt-8">
      <Strip step={step} onPick={sheet.setStep} />
      <div>
        <div className={t.assessEyebrow}>{`Step ${step + 1} of 4`}</div>
        <h2 className={t.assessTitle}>{HEADINGS[step]!.title}</h2>
        <p className={cn(t.assessDesc, "m-0")}>{HEADINGS[step]!.lead}</p>
      </div>
      <div className={step === 1 ? "flex flex-col gap-[18px]" : step === 3 ? `${boardCardClipped} p-7` : `${boardCardClipped} flex flex-col gap-[18px] p-7`}>
        {step === 0 ? (
          <>
            {ours && !first ? (
              <Link href={hrefFor("/programmes")} className="flex flex-col gap-1 rounded-board border border-osce-accent bg-assess-selected-bg px-[18px] py-4 text-left text-ink no-underline">
                <span className="text-assess-desc font-medium !leading-[normal]">{ours.title}</span>
                <span className="text-assess-meta text-ink-subtle">{ours.body}</span>
              </Link>
            ) : null}
            <BoardField label="Exam name">
              <input
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                className={boardInput}
                placeholder="Paediatrics block"
              />
            </BoardField>
          </>
        ) : null}

        {step === 1 ? (
          <>
            <div role="radiogroup" aria-label="Marking scheme" className="flex flex-col gap-2.5">
              {SCHEME_WAYS.map((option) => {
                const on = way === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => sheet.setWay(option.id)}
                    className={cn(
                      "flex w-full items-start gap-3.5 rounded-board border px-[18px] py-4 text-left text-ink",
                      on ? "border-osce-accent bg-assess-selected-bg" : "border-osce-border bg-osce-surface",
                    )}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "mt-0.5 size-[18px] shrink-0 rounded-full border bg-osce-surface",
                        on ? "border-[5px] border-osce-accent" : "border-osce-border",
                      )}
                    />
                    <span className="flex min-w-0 flex-col">
                      <span className="text-assess-desc font-medium !leading-[normal]">{schemeWayTitle(option.id, option.title, w)}</span>
                      <span className="truncate text-assess-meta text-ink-subtle">
                        {option.id === "use"
                          ? versions.length > 0
                            ? versions.map((v) => v.label).join(", ")
                            : "You have no published marking scheme yet."
                          : option.body}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
            {way === "use" ? (
              <BoardField label="Marking scheme version">
                <Select
                  value={draft.rubricVersionId}
                  onChange={(e) => setDraft({ ...draft, rubricVersionId: e.target.value })}
                >
                  <option value="">{rubrics.error ? "Marking schemes could not be loaded" : "None yet"}</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.label}
                    </option>
                  ))}
                </Select>
                {rubrics.error ? <LoadError message={rubrics.error.message} onRetry={rubrics.reload} /> : null}
              </BoardField>
            ) : (
              way === "write" ? (
                <p className={cn(t.assessMeta, "m-0")}>
                  Opens the scheme builder. When you publish the scheme, you come straight back here.
                </p>
              ) : null
            )}
          </>
        ) : null}

        {step === 2 ? (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <BoardField label="Reading time">
                <input type="number" min={1} max={MAX_READING_MIN} value={minutes.reading} onChange={(e) => setMinutes("reading", e.target.value)} className={boardInput} />
                <span className="block text-assess-meta text-ink-subtle">{`1 to ${MAX_READING_MIN} min`}</span>
              </BoardField>
              <BoardField label="Consultation">
                <input type="number" min={1} max={MAX_CONSULT_MIN} value={minutes.simulation} onChange={(e) => setMinutes("simulation", e.target.value)} className={boardInput} />
                <span className="block text-assess-meta text-ink-subtle">{`1 to ${MAX_CONSULT_MIN} min`}</span>
              </BoardField>
              <BoardField label="Break">
                <input type="number" min={1} max={MAX_BREAK_MIN} value={minutes.breakMin} onChange={(e) => setBreak(e.target.value)} className={boardInput} />
                <span className="block text-assess-meta text-ink-subtle">{`1 to ${MAX_BREAK_MIN} min, formal exams`}</span>
              </BoardField>
            </div>
            {timings ? <Alert tone="danger">{timings}</Alert> : null}
            <ExamSettingsFields
              title="More settings"
              description="Patient voice, feedback style and the AI writing setup. The same options as today's exam settings."
              value={draft.settings}
              onChange={(patch) => setDraft({ ...draft, settings: { ...draft.settings, ...patch } })}
              bare
              lead={
                <BoardField label="Attempts per station">
                  <input type="number" min={1} value={draft.attempts} onChange={(e) => setDraft({ ...draft, attempts: e.target.value })} className={boardInput} />
                </BoardField>
              }
            />
          </>
        ) : null}

        {step === 3 ? (
          <>
            <dl className="text-assess-label">
              <Row term="Exam" value={draft.name.trim()} first />
              <Row term="Marking scheme" value={schemeLabel} />
              <Row term="Timings" value={timingsLine(minutes)} />
              <Row term="Available for scheduling" value="On after publishing" chip />
            </dl>
          </>
        ) : null}

        {error && !failedStep ? <Alert tone="danger">{error}</Alert> : null}
        {step === 0 && nameProblem && draft.name !== "" ? <p className="text-osce-caption text-ink-muted">{nameProblem}</p> : null}

      </div>
        {step === 3 ? (
          <>
            <p className={cn(t.assessMeta, "m-0")}>
              If a step fails, the exam is kept as it is and this screen says which step to retry. Nothing is half made.
            </p>
            {failedStep ? (
              <Alert tone="danger">
                {`${PUBLISH_STEP_WORDS[failedStep]} did not finish: ${error ?? "try again"}. Your exam is kept as it is; retry to carry on from this step.`}
              </Alert>
            ) : null}
          </>
        ) : null}
        <div className="flex justify-between gap-4">
          <button type="button" className={boardBtn()} disabled={step === 0 || busy} onClick={() => sheet.setStep(step - 1)}>
            Back
          </button>
          {step === 1 && way !== "use" ? (
            /* Copy and write both go to the builder's start screen (OSCE Guide's schemes, or a blank one); coming back resumes here. */
            <button type="button" className={boardBtn()} onClick={() => router.push(`${rubricNewPath(hrefFor)}${examQuery(exam?.id)}`)}>
              {way === "copy" ? "Choose one to copy" : "Open the scheme builder"}
            </button>
          ) : null}
          {step < 3 ? (
            <button type="button" className={boardBtn("primary")} disabled={!sheet.canContinue || busy} onClick={() => void sheet.advance()}>
              {busy ? "Saving…" : "Continue"}
            </button>
          ) : (
            <button type="button" className={boardBtn("primary")} disabled={busy || !exam} onClick={() => void sheet.publish()}>
              {busy ? "Publishing…" : failedStep ? "Retry" : "Publish exam"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const headings = (w: AssessWords) => [
  { title: "Name your exam", lead: newExamNameLead(w) },
  { title: "How will it be marked?", lead: "The marking scheme lists the domains reviewers rate and how. You can change it later as a new version." },
  { title: "Timings and settings", lead: newExamTimingsLead(w) },
  { title: "Ready to publish", lead: "Publishing makes the exam available for scheduling. Add stations next." },
] as const;

/** The board's `.strip`: four step buttons, the current one raised, finished ones green. */
function Strip({ step, onPick }: { step: number; onPick: (index: number) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {NEW_EXAM_STEPS.map((label, index) => {
        const on = index === step;
        const done = index < step;
        return (
          <button
            key={label}
            type="button"
            aria-current={on ? "step" : undefined}
            disabled={index > step}
            onClick={() => onPick(index)}
            className={cn(
              "flex min-h-12 flex-[1_1_140px] items-center gap-2.5 rounded-board px-3 py-2.5 disabled:opacity-100 text-left text-assess-meta !leading-[normal]",
              on ? "border border-osce-border bg-osce-surface font-medium text-ink" : "border-0 text-ink-subtle",
              done && "text-ink",
            )}
          >
            <span
              className={cn(
                "flex size-[26px] shrink-0 items-center justify-center rounded-full border text-assess-chip",
                on ? "border-osce-accent text-osce-accent bg-osce-surface" : "border-osce-border bg-osce-surface",
                done && "border-osce-success-text bg-osce-success-text text-white",
              )}
            >
              {done ? "\u2713" : index + 1}
            </span>
            {label}
          </button>
        );
      })}
    </div>
  );
}

/** The board's `label` + control: 14px/500 label, 6px to the control, a 13px hint below. */
function BoardField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="block text-assess-label font-medium text-ink">{label}</span>
      {children}
    </label>
  );
}

function Row({ term, value, first, chip }: { term: string; value: string; first?: boolean; chip?: boolean }) {
  return (
    <div className={cn("flex flex-wrap justify-between gap-4 py-3", !first && "border-t border-osce-border-light")}>
      <dt className={t.assessMeta}>{term}</dt>
      <dd className="m-0 text-ink">{chip ? <BoardChip tone="ok">{value}</BoardChip> : value}</dd>
    </div>
  );
}
