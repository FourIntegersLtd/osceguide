"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSurface } from "@/capabilities";
import { createExam, listExams, type Exam, type Programme } from "@/capabilities/authoring/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { authoringErrorMessage } from "@/capabilities/authoring/lib/authoringError";
import { isPlatformError } from "@/foundation/platform-client/errors";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { applyStep, saveExam } from "@/capabilities/authoring/exams/offer";
import { examDetailPath } from "@/capabilities/authoring/exams/paths";
import { createWithFreshCode, resumeStep, timingProblem, toMinutes } from "@/capabilities/authoring/exams/newExam";
import { examResumePath } from "@/capabilities/authoring/templates/paths";
import { loadExam } from "@/capabilities/authoring/exams/useExam";
import { blankExam, examToDraft, type ExamDraft } from "@/capabilities/authoring/sections/ExamFields";
import { publishPlan, type PublishStep } from "@/capabilities/authoring/sections/examSteps";

export type SchemeWay = "use" | "copy" | "write";

/** The sheet's defaults: 3 minutes reading, 10 consultation. */
const START: ExamDraft = { ...blankExam, reading: "180", simulation: "600" };

/** State and writes of the New exam sheet: each step saves the draft, so a reload resumes it. */
export function useNewExam(first: Exam | null, firstProgramme: Programme | null) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const router = useRouter();

  const [exam, setExam] = useState<Exam | null>(first);
  const [programme, setProgramme] = useState<Programme | null>(firstProgramme);
  const [step, setStep] = useState(resumeStep(first));
  const [draft, setDraft] = useState<ExamDraft>(first ? examToDraft(first) : START);
  const [way, setWay] = useState<SchemeWay>("use");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failedStep, setFailedStep] = useState<PublishStep | null>(null);
  // Set once a create was sent: if it failed, the exam may still have been made, so the retry looks first.
  const [sentCode, setSentCode] = useState<string | null>(null);

  const minutes = {
    reading: String(toMinutes(draft.reading)),
    simulation: String(toMinutes(draft.simulation)),
    breakMin: draft.settings.default_break_minutes != null ? String(draft.settings.default_break_minutes) : "",
  };
  const timings = step === 2 ? timingProblem(minutes) : null;
  const nameProblem =
    draft.name.trim() === "" ? "Name the exam." : null;
  const canContinue = step === 0 ? nameProblem === null : step === 1 ? draft.rubricVersionId !== "" : step === 2 ? timings === null : true;

  async function save(work: () => Promise<Exam>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      setExam(await work());
      return true;
    } catch (cause) {
      setError(authoringErrorMessage(cause, w));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    if (step === 0) {
      const ok = await save(async () => {
        if (exam) return saveExam(scope, exam, { name: draft.name.trim() });
        if (sentCode) {
          const earlier = (await listExams(scope, { status: "all" })).items.find((item) => item.code === sentCode);
          if (earlier) {
            router.replace(examResumePath(hrefFor, earlier.id));
            return earlier;
          }
        }
        const made = await createWithFreshCode(
          draft.name,
          (cause) => isPlatformError(cause) && cause.status === 409,
          (code) => {
            setSentCode(code);
            return createExam(scope, {
              code,
              name: draft.name.trim(),
              default_reading_seconds: Number(draft.reading),
              default_simulation_seconds: Number(draft.simulation),
              station_attempt_limit: Number(draft.attempts),
              partner_pilot: false,
              settings: draft.settings,
            });
          },
        );
        // Its own address: a reload or a later visit resumes this draft.
        router.replace(examResumePath(hrefFor, made.id));
        return made;
      });
      if (ok) setStep(1);
    } else if (step === 1 && exam) {
      if (await save(() => saveExam(scope, exam, { rubric_version_id: draft.rubricVersionId }))) setStep(2);
    } else if (step === 2 && exam) {
      const ok = await save(() =>
        saveExam(scope, exam, {
          default_reading_seconds: Number(draft.reading),
          default_simulation_seconds: Number(draft.simulation),
          station_attempt_limit: Number(draft.attempts) || 3,
          settings: draft.settings,
        }),
      );
      if (ok) setStep(3);
    }
  }

  /** Publish, create the programme, activate it. Each write is planned from fresh state, so a retry resumes. */
  async function publish() {
    if (!exam) return;
    setBusy(true);
    setError(null);
    setFailedStep(null);
    // Read afresh: a write that committed before a failure (or a lost reply) must not be sent twice.
    let state: { exam: Exam; programme: Programme | null } = { exam, programme };
    try {
      state = (await loadExam(scope, exam.id)) ?? state;
    } catch (cause) {
      setError(authoringErrorMessage(cause, w));
      setBusy(false);
      return;
    }
    for (const next of publishPlan(state.exam, state.programme)) {
      try {
        state = await applyStep(scope, next, state);
      } catch (cause) {
        setExam(state.exam);
        setProgramme(state.programme);
        setFailedStep(next);
        setError(authoringErrorMessage(cause, w));
        setBusy(false);
        return;
      }
    }
    router.push(examDetailPath(hrefFor, state.exam.id));
  }

  return {
    exam,
    step,
    setStep,
    draft,
    setDraft,
    way,
    setWay,
    busy,
    error,
    failedStep,
    minutes,
    timings,
    nameProblem,
    canContinue,
    advance,
    publish,
  };
}
