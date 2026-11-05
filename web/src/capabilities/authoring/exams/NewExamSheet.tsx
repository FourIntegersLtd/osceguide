"use client";

import { useState } from "react";
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
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  addProgramme,
  createExam,
  listExams,
  listProgrammes,
  publishExam,
  updateExam,
  updateProgramme,
  type Exam,
  type ExamSettings,
  type Programme,
} from "@/capabilities/authoring/api";
import { staleRefusal } from "@/capabilities/authoring/api/stale";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { examDetailPath, examNewPath, examsListPath } from "@/capabilities/authoring/exams/paths";
import {
  NEW_EXAM_STEPS,
  MAX_CONSULT_MIN,
  MAX_READING_MIN,
  nextPublishStep,
  PUBLISH_STEP_WORDS,
  resumeStep,
  timingProblem,
  timingsLine,
  type PublishStep,
} from "@/capabilities/authoring/exams/newExam";
import { blankExam, useSchemeVersions } from "@/capabilities/authoring/sections/ExamFields";
import { ExamSettingsFields, Field } from "@/capabilities/authoring/sections/ExamSettingsFields";
import { rubricNewPath } from "@/capabilities/authoring/templates/paths";

const SCHEME_WAYS = [
  { id: "use", title: "Use one of your marking schemes" },
  { id: "copy", title: "Copy one from OSCE Guide", body: "Start from a tested scheme and change what you need." },
  { id: "write", title: "Write a new marking scheme", body: "Name the areas, the ratings and what each means." },
] as const;
type SchemeWay = (typeof SCHEME_WAYS)[number]["id"];

const CODE_PATTERN = /^[A-Za-z0-9-]{2,32}$/;

/** "New exam": one sheet that makes the exam, picks its marking scheme, sets timings, then publishes and offers it. */
export function NewExamSheet() {
  const scope = useAuthoringScope();
  const examId = useSearchParams().get("exam");
  // A saved draft is read back so the sheet resumes where it stopped.
  const saved = useAsync(
    async (signal) => {
      if (!examId) return { exam: null, programme: null };
      const exams = await listExams(scope, { status: "all" }, signal);
      const exam = exams.items.find((item) => item.id === examId) ?? null;
      const programmes = exam ? await listProgrammes(scope, signal) : null;
      return { exam, programme: programmes?.items.find((p) => p.exam_code === exam?.code) ?? null };
    },
    [scope.base, examId],
  );
  return (
    <RequireAuthor>
      <AsyncBoundary state={saved}>
        {({ exam, programme }) => <Sheet key={exam?.id ?? "new"} first={exam} firstProgramme={programme} />}
      </AsyncBoundary>
    </RequireAuthor>
  );
}

function Sheet({ first, firstProgramme }: { first: Exam | null; firstProgramme: Programme | null }) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();

  const [exam, setExam] = useState<Exam | null>(first);
  const [programme, setProgramme] = useState<Programme | null>(firstProgramme);
  const [step, setStep] = useState(resumeStep(first));
  const [name, setName] = useState(first?.name ?? "");
  const [code, setCode] = useState(first?.code ?? "");
  const [schemeId, setSchemeId] = useState(first?.rubric_version_id ?? "");
  const [way, setWay] = useState<SchemeWay>("use");
  const [reading, setReading] = useState(first ? String(Math.round(first.default_reading_seconds / 60)) : "3");
  const [simulation, setSimulation] = useState(first ? String(Math.round(first.default_simulation_seconds / 60)) : "10");
  const [attempts, setAttempts] = useState(first ? String(first.station_attempt_limit) : "3");
  const [settings, setSettings] = useState<ExamSettings>(first?.settings ?? blankExam.settings);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failedStep, setFailedStep] = useState<Exclude<PublishStep, "done"> | null>(null);

  const { rubrics, versions } = useSchemeVersions(schemeId);
  const schemeLabel = versions.find((v) => v.id === schemeId)?.label ?? "None chosen";
  const minutes = { reading, simulation };
  const problem = step === 2 ? timingProblem(minutes) : null;

  const steps: RailStep[] = NEW_EXAM_STEPS.map((label, index) => ({
    id: label,
    label,
    state: index < step ? "done" : "todo",
    note: "",
  }));

  const nameProblem =
    name.trim() === ""
      ? "Name the exam."
      : !exam && !CODE_PATTERN.test(code.trim())
        ? "The short code is 2 to 32 letters, numbers or dashes."
        : null;

  const canContinue =
    step === 0 ? nameProblem === null : step === 1 ? schemeId !== "" : step === 2 ? problem === null : true;

  async function save(work: () => Promise<Exam>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      setExam(await work());
      return true;
    } catch (cause) {
      const stale = staleRefusal(cause, "exam");
      setError(stale ? stale.message : errorMessage(cause));
      return false;
    } finally {
      setBusy(false);
    }
  }

  const seconds = { reading: Number(reading) * 60, simulation: Number(simulation) * 60 };

  async function advance() {
    if (step === 0) {
      const ok = await save(async () => {
        if (exam) return updateExam(scope, exam.id, { revision: exam.revision, name: name.trim() });
        const made = await createExam(scope, {
          code: code.trim(),
          name: name.trim(),
          default_reading_seconds: 180,
          default_simulation_seconds: 600,
          station_attempt_limit: 3,
          partner_pilot: false,
          settings,
        });
        // Its own address: a reload or a later visit resumes this draft.
        router.replace(`${examNewPath(hrefFor)}?exam=${encodeURIComponent(made.id)}`);
        return made;
      });
      if (ok) setStep(1);
    } else if (step === 1 && exam) {
      if (await save(() => updateExam(scope, exam.id, { revision: exam.revision, rubric_version_id: schemeId }))) setStep(2);
    } else if (step === 2 && exam) {
      const ok = await save(() =>
        updateExam(scope, exam.id, {
          revision: exam.revision,
          default_reading_seconds: seconds.reading,
          default_simulation_seconds: seconds.simulation,
          station_attempt_limit: Number(attempts) || 3,
          settings,
        }),
      );
      if (ok) setStep(3);
    }
  }

  /** Publish, create the programme, activate it: each skipped when already done, so a retry resumes. */
  async function publish() {
    if (!exam) return;
    setBusy(true);
    setError(null);
    setFailedStep(null);
    let current = exam;
    let prog = programme;
    for (;;) {
      const next = nextPublishStep(current, prog);
      if (next === "done") break;
      try {
        if (next === "publish") current = await publishExam(scope, current.id);
        else if (next === "programme") prog = await addProgramme(scope, current.code);
        else if (prog) prog = await updateProgramme(scope, prog.id, "active");
      } catch (cause) {
        setExam(current);
        setProgramme(prog);
        setFailedStep(next);
        setError(errorMessage(cause));
        setBusy(false);
        return;
      }
    }
    router.push(examDetailPath(hrefFor, current.id));
  }

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
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={`mt-1 ${getInputClassName()}`}
                placeholder="Paediatrics block"
              />
            </Field>
            <Field label="Short code">
              <input
                value={code}
                disabled={exam !== null}
                onChange={(e) => setCode(e.target.value)}
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
                <SelectableCard key={option.id} selected={way === option.id} onSelect={() => setWay(option.id)}>
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
                <Select value={schemeId} onChange={(e) => setSchemeId(e.target.value)} className="mt-1">
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
                <Button
                  variant="secondary"
                  onClick={() => router.push(`${rubricNewPath(hrefFor)}?exam=${encodeURIComponent(exam?.id ?? "")}`)}
                >
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
                <input type="number" min={1} max={MAX_READING_MIN} value={reading} onChange={(e) => setReading(e.target.value)} className={`mt-1 ${getInputClassName()}`} />
                <span className="mt-1 block text-osce-caption text-ink-muted">{`1 to ${MAX_READING_MIN} min`}</span>
              </Field>
              <Field label="Consultation">
                <input type="number" min={1} max={MAX_CONSULT_MIN} value={simulation} onChange={(e) => setSimulation(e.target.value)} className={`mt-1 ${getInputClassName()}`} />
                <span className="mt-1 block text-osce-caption text-ink-muted">{`1 to ${MAX_CONSULT_MIN} min`}</span>
              </Field>
              <Field label="Attempts per station">
                <input type="number" min={1} value={attempts} onChange={(e) => setAttempts(e.target.value)} className={`mt-1 ${getInputClassName()}`} />
              </Field>
            </div>
            <p className="text-osce-caption text-ink-muted">
              The break between stations is set per circuit when you schedule a formal sitting.
            </p>
            {problem ? <Alert tone="danger">{problem}</Alert> : null}
            <ExamSettingsFields
              title="More settings"
              value={settings}
              onChange={(patch) => setSettings({ ...settings, ...patch })}
            />
          </>
        ) : null}

        {step === 3 ? (
          <>
            <Heading title="Ready to publish" lead="Publishing makes the exam available for scheduling. Add stations next." />
            <dl className="divide-y divide-border text-osce-body">
              <Row term="Exam" value={`${name.trim()} · ${(exam?.code ?? code).trim()}`} />
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
        {step === 0 && nameProblem && name !== "" ? <p className="text-osce-caption text-ink-muted">{nameProblem}</p> : null}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <Button variant="secondary" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>
            Back
          </Button>
          {step < 3 ? (
            <Button variant="primary" disabled={!canContinue || busy} onClick={() => void advance()}>
              {busy ? "Saving…" : "Continue"}
            </Button>
          ) : (
            <Button variant="primary" disabled={busy || !exam} onClick={() => void publish()}>
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
