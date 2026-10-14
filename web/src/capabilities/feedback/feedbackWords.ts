import { toneWord } from "./rubric";

/** A grade in words: its tone ("Good"), or the rubric's own letter when it gave no tone. */
export function gradeWord(grade: string, tone: string | null): string {
  return tone ? toneWord(tone) : grade;
}

/** "2 competencies graded Good". A grade nobody got has no tally. */
export function gradeTallyText(count: number, grade: string, tone: string | null): string | null {
  if (count <= 0) return null;
  return `${count} ${count === 1 ? "competency" : "competencies"} graded ${gradeWord(grade, tone)}`;
}

/** The live checklist's total, saying what was counted and when. */
export function coverageSummary(covered: number, total: number): string {
  const suffix = "fully covered during the consultation";
  if (covered === 0 && total === 1) return `The item was not ${suffix}`;
  if (total === 1) return `The item was ${suffix}`;
  if (covered === 0) return `None of the ${total} items ${suffix}`;
  if (covered === total) return `All ${total} items ${suffix}`;
  return `${covered} of ${total} items ${suffix}`;
}
