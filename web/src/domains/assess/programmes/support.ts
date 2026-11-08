import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import { hasCode } from "@/foundation/platform-client";

/** A refused adoption said in plain words, or null for a failure that is not a refusal. */
export function adoptRefusal(cause: unknown): string | null {
  if (hasCode(cause, "exam_already_imported")) return "Your organisation already runs that exam. It is in your programmes below.";
  if (hasCode(cause, "unknown_exam")) return "The platform no longer offers that exam. The list has been refreshed.";
  return null;
}

/** The programmes page's words: an employer's programme is an exam, and it runs assessments. */
export const programmesCopy = (w: AssessWords) => ({
  title: w.hiring ? "Offered exams" : "Programmes",
  yours: w.hiring ? "Your offered exams" : "Your programmes",
  subtitle: w.hiring
    ? `An exam you run ${w.sittings} against. Adopt one the platform publishes or add your own, activate it, and it is offered when you schedule an ${w.sitting}.`
    : "A programme is an exam you run sittings against. Adopt one the platform publishes or add your own, activate it, and it is offered when you schedule a sitting.",
});
