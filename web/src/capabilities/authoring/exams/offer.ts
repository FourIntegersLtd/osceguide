import {
  addProgramme,
  publishExam,
  updateExam,
  updateProgramme,
  type Exam,
  type Programme,
} from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import { staleRefusal } from "@/capabilities/authoring/api/stale";
import type { PublishStep } from "@/capabilities/authoring/sections/examSteps";

export type OfferState = { exam: Exam; programme: Programme | null };

/** One write of the publish and offer plan; returns the state it leaves, for the next step. */
export async function applyStep(scope: AuthoringScope, step: PublishStep, state: OfferState): Promise<OfferState> {
  if (step === "publish") return { ...state, exam: await publishExam(scope, state.exam.id) };
  if (step === "add") return { ...state, programme: await addProgramme(scope, state.exam.code) };
  if (!state.programme) return state;
  const status = step === "activate" ? "active" : "retired";
  return { ...state, programme: await updateProgramme(scope, state.programme.id, status) };
}

/**
 * Saves an exam by its revision. A stale revision becomes the shared refusal, after `onStale`
 * has let the caller reload so the next read shows the other person's version.
 */
export async function saveExam(
  scope: AuthoringScope,
  exam: Exam,
  patch: Omit<Parameters<typeof updateExam>[2], "revision">,
  onStale?: () => void,
): Promise<Exam> {
  try {
    return await updateExam(scope, exam.id, { ...patch, revision: exam.revision });
  } catch (cause) {
    const stale = staleRefusal(cause, "exam");
    if (!stale) throw cause;
    onStale?.();
    throw stale;
  }
}
