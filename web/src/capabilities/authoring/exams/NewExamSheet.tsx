"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  Alert,
  AsyncBoundary,
  B2CPageHeader,
  Button,
  getInputClassName,
  Panel,
  Select,
  SelectableCard,
  StepRail,
  type RailStep,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { Exam, Programme } from "@/capabilities/authoring/api";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { examsListPath } from "@/capabilities/authoring/exams/paths";
import {
  NEW_EXAM_STEPS,
  MAX_CONSULT_MIN,
  MAX_READING_MIN,
  PUBLISH_STEP_WORDS,
  timingsLine,
} from "@/capabilities/authoring/exams/newExam";
import { useNewExam, type SchemeWay } from "@/capabilities/authoring/exams/useNewExam";
import { useExam } from "@/capabilities/authoring/exams/useExam";
import { useSchemeVersions } from "@/capabilities/authoring/sections/ExamFields";
import { ExamSettingsFields, Field } from "@/capabilities/authoring/sections/ExamSettingsFields";
import { examQuery, rubricNewPath } from "@/capabilities/authoring/templates/paths";

const SCHEME_WAYS: { id: SchemeWay; title: string; body?: string }[] = [
  { id: "use", title: "Use one of your marking schemes" },
  { id: "copy", title: "Copy one from OSCE Guide", body: "Start from a tested scheme and change what you need." },
  { id: "write", title: "Write a new marking scheme", body: "Name the areas, the ratings and what each means." },
];

/** "New exam": one sheet that makes the exam, picks its marking scheme, sets timings, then publishes and offers it. */
export function NewExamSheet() {
  const examId = useSearchParams().get("exam");
  // A saved draft is read back so the sheet resumes where it stopped.
  const saved = useExam(examId);
  return (
    <RequireAuthor>
      <AsyncBoundary state={saved}>
        {(found) => <Sheet key={found?.exam.id ?? "new"} first={found?.exam ?? null} firstProgramme={found?.programme ?? null} />}
      </AsyncBoundary>
    </RequireAuthor>
  );
}

function Sheet({ first, firstProgramme }: { first: Exam | null; firstProgramme: Programme | null }) {
  const { hrefFor } = useSurface();
  const router = useRouter();
  const sheet = useNewExam(first, firstProgramme);
  const { draft, setDraft, step, busy, error, failedStep, minutes, timings, nameProblem, exam, way } = sheet;
  const { rubrics, versions } = useSchemeVersions(draft.rubricVersionId);
  const schemeLabel = versions.find((v) => v.id === draft.rubricVersionId)?.label ?? "None chosen";

  const steps: RailStep[] = NEW_EXAM_STEPS.map((label, index) => ({
    id: label,
    label,
    state: index < step ? "done" : "todo",
    note: "",
  }));

  const setMinutes = (field: "reading" | "simulation", value: string) =>
    setDraft({ ...draft, [field]: String(Math.round(Number(value) * 60)) });

  return (
    <div className="flex flex-col gap-6 pb-8">
      <B2CPageHeader
        eyebrow="Your progress is saved after each step"
        title="New exam"
        back={{ href: examsListPath(hrefFor), label: "Close" }}
      />
      <StepRail steps={steps} current={NEW_EXAM_STEPS[step]} />
      <Panel className="flex flex-col gap-5">
        <p className="text-osce-caption font-medium uppercase tracking-wide text-ink-subtle">{`Step ${step + 1} of 4`}</p>

        {step === 0 ? (
          <>
            <Heading title="Name your exam" lead="This is what supervisors and trainees will see on every sitting." />
            <Field label="Exam name">
              <input
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                className={`mt-1 ${getInputClassName()}`}
                placeholder="Paediatrics block"
              />
            </Field>
            <Field label="Short code">
              <input
                value={draft.code}
                disabled={exam !== null}
                onChange={(e) => setDraft({ ...draft, code: e.target.value })}
                className={`mt-1 ${getInputClassName()}`}
                placeholder="PAED"
              />
              <span className="mt-1 block text-osce-caption text-ink-muted">
                Letters, numbers and dashes. It can&apos;t be the same as another of your exams.
              </span>
            </Field>
          </>
        ) : null}

        {step === 1 ? (
          <>
            <Heading
              title="How will it be marked?"
              lead="The marking scheme lists the areas reviewers rate and how. You can change it later as a new version."
            />
            <div role="radiogroup" aria-label="Marking scheme" className="grid gap-3">
              {SCHEME_WAYS.map((option) => (
                <SelectableCard key={option.id} selected={way === option.id} onSelect={() => sheet.setWay(option.id)}>
                  <span className="text-osce-body font-semibold text-ink">{option.title}</span>
                  <span className="text-osce-caption text-ink-muted">
                    {option.id === "use"
                      ? versions.length > 0
                        ? versions.map((v) => v.label).join(", ")
                        : "You have no published marking scheme yet."
                      : option.body}
                  </span>
                </SelectableCard>
              ))}
            </div>
            {way === "use" ? (
              <Field label="Marking scheme version">
                <Select
                  value={draft.rubricVersionId}
                  onChange={(e) => setDraft({ ...draft, rubricVersionId: e.target.value })}
                  className="mt-1"
                >
                  <option value="">{rubrics.error ? "Marking schemes could not be loaded" : "None yet"}</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.label}
                    </option>
                  ))}
                </Select>
                {rubrics.error ? <LoadError message={rubrics.error.message} onRetry={rubrics.reload} /> : null}
              </Field>
            ) : (
              <div className="flex flex-col items-start gap-2">
                {/* Both go to the builder's start screen, which offers Start from cards (OSCE Guide's schemes) and a blank one. */}
                <Button variant="secondary" onClick={() => router.push(`${rubricNewPath(hrefFor)}${examQuery(exam?.id)}`)}>
                  {way === "copy" ? "Choose one to copy" : "Open the scheme builder"}
                </Button>
                <p className="text-osce-caption text-ink-muted">
                  Opens the scheme builder. When you publish the scheme, you come straight back here.
                </p>
              </div>
            )}
          </>
        ) : null}

        {step === 2 ? (
          <>
            <Heading
              title="Timings and settings"
              lead="These are the defaults for every circuit. You can change them per circuit when you schedule."
            />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Reading time">
                <input type="number" min={1} max={MAX_READING_MIN} value={minutes.reading} onChange={(e) => setMinutes("reading", e.target.value)} className={`mt-1 ${getInputClassName()}`} />
                <span className="mt-1 block text-osce-caption text-ink-muted">{`1 to ${MAX_READING_MIN} min`}</span>
              </Field>
              <Field label="Consultation">
                <input type="number" min={1} max={MAX_CONSULT_MIN} value={minutes.simulation} onChange={(e) => setMinutes("simulation", e.target.value)} className={`mt-1 ${getInputClassName()}`} />
                <span className="mt-1 block text-osce-caption text-ink-muted">{`1 to ${MAX_CONSULT_MIN} min`}</span>
              </Field>
              <Field label="Attempts per station">
                <input type="number" min={1} value={draft.attempts} onChange={(e) => setDraft({ ...draft, attempts: e.target.value })} className={`mt-1 ${getInputClassName()}`} />
              </Field>
            </div>
            <p className="text-osce-caption text-ink-muted">
              The break between stations is set per circuit when you schedule a formal sitting.
            </p>
            {timings ? <Alert tone="danger">{timings}</Alert> : null}
            <ExamSettingsFields
              title="More settings"
              value={draft.settings}
              onChange={(patch) => setDraft({ ...draft, settings: { ...draft.settings, ...patch } })}
            />
          </>
        ) : null}

        {step === 3 ? (
          <>
            <Heading title="Ready to publish" lead="Publishing makes the exam available for scheduling. Add stations next." />
            <dl className="divide-y divide-border text-osce-body">
              <Row term="Exam" value={`${draft.name.trim()} · ${draft.code.trim()}`} />
              <Row term="Marking scheme" value={schemeLabel} />
              <Row term="Timings" value={timingsLine(minutes)} />
              <Row term="Available for scheduling" value="On after publishing" />
            </dl>
            <p className="text-osce-caption text-ink-muted">
              If a step fails, the exam is kept as it is and this screen says which step to retry. Nothing is half made.
            </p>
            {failedStep ? (
              <Alert tone="danger">
                {`${PUBLISH_STEP_WORDS[failedStep]} did not finish: ${error ?? "try again"}. Your exam is kept as it is; retry to carry on from this step.`}
              </Alert>
            ) : null}
          </>
        ) : null}

        {error && !failedStep ? <Alert tone="danger">{error}</Alert> : null}
        {step === 0 && nameProblem && draft.name !== "" ? <p className="text-osce-caption text-ink-muted">{nameProblem}</p> : null}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <Button variant="secondary" disabled={step === 0 || busy} onClick={() => sheet.setStep(step - 1)}>
            Back
          </Button>
          {step < 3 ? (
            <Button variant="primary" disabled={!sheet.canContinue || busy} onClick={() => void sheet.advance()}>
              {busy ? "Saving…" : "Continue"}
            </Button>
          ) : (
            <Button variant="primary" disabled={busy || !exam} onClick={() => void sheet.publish()}>
              {busy ? "Publishing…" : failedStep ? "Retry" : "Publish exam"}
            </Button>
          )}
        </div>
      </Panel>
    </div>
  );
}

function Heading({ title, lead }: { title: string; lead: string }) {
  return (
    <div>
      <h2 className="text-osce-title font-semibold text-ink">{title}</h2>
      <p className="mt-1 text-osce-body text-ink-muted">{lead}</p>
    </div>
  );
}

function Row({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex flex-wrap justify-between gap-2 py-2">
      <dt className="text-ink-muted">{term}</dt>
      <dd className="text-ink">{value}</dd>
    </div>
  );
}
