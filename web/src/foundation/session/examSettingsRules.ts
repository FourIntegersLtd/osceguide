import type { ExamSettings } from "@/foundation/session/useCurrentExam";

/**
 * The pure decisions a screen makes from one exam's `settings`.
 *
 * `settings` is the single source for what differs between exams
 * (`app/core/exam_settings.py`) — an exam is data, not code, so nothing here
 * may branch on an exam code or a hardcoded name. Kept as plain functions,
 * away from the components that call them, so a settings shape can be tested
 * with a literal object rather than by rendering a screen.
 */

/** Whether the help dock has a real choice to offer, and which way it opens when it does not. */
export function helpModeChoice(settings: ExamSettings): {
  offersChoice: boolean;
  opensDirectlyOnKnowledge: boolean;
} {
  const modes = settings.help_modes ?? ["navigate"];
  const offersChoice = modes.includes("navigate") && modes.includes("knowledge_base");
  const opensDirectlyOnKnowledge = !offersChoice && modes.includes("knowledge_base");
  return { offersChoice, opensDirectlyOnKnowledge };
}

/** Whether this exam offers a "practise as patient" peer session, alongside debrief. */
export function offersPatientPractice(settings: ExamSettings): boolean {
  const modes = settings.session_modes ?? ["debrief", "practice_as_patient"];
  return modes.includes("practice_as_patient");
}

/** Whether this exam shows consultation tips while a candidate waits on marking. */
export function showsMarkingTips(settings: ExamSettings): boolean {
  return settings.show_tips_while_marking;
}

/** Whether this exam splits its stations into named sub-types (ST3 T&O's interview, portfolio, clinical). */
export function hasStationSubtypes(settings: ExamSettings): boolean {
  return (settings.station_subtypes?.length ?? 0) > 0;
}
