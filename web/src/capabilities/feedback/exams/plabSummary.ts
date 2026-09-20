import type { PlabFeedbackData, PlabFeedbackType } from "./plabTypes";

/** The B2C backend's three domain sums, each made of four scores out of one. */
export function plabSummary(feedback: Pick<PlabFeedbackData | PlabFeedbackType,
  "data_gathering" | "clinical_management" | "interpersonal_skills" | "passed_station"
>) {
  const dg = feedback.data_gathering;
  const cm = feedback.clinical_management;
  const interpersonal = feedback.interpersonal_skills;
  const domains = [
    [dg.history_taking, dg.examination, dg.investigations, dg.interpretation],
    [cm.diagnosis, cm.management_plan, cm.safety_netting, cm.follow_up],
    [interpersonal.language, interpersonal.listening, interpersonal.rapport, interpersonal.empathy],
  ].map((cells) => cells.reduce((sum, cell) => sum + cell.score, 0));
  const total = domains.reduce((sum, score) => sum + score, 0);
  return { total, passed: typeof feedback.passed_station === "boolean"
    ? feedback.passed_station : total >= 7 && domains.every((score) => score >= 2) };
}
