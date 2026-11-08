/** The sitting page's words that differ between an institution and an employer (boards HireAssessment). Pure, so they are pinned by tests. */
import type { AssessWords } from "@/capabilities/assess-words";

/** The empty Circuits tab. */
export function circuitsEmpty(w: AssessWords): { title: string; body: string } {
  return {
    title: `No ${w.circuits} yet`,
    body: `Add at least one ${w.circuit} so candidates can take this ${w.sitting}.`,
  };
}

/** The empty Candidates tab. */
export function candidatesEmptyBody(w: AssessWords): string {
  return `Add a ${w.circuit} to put ${w.hiring ? "candidates" : "people"} on this ${w.sitting}.`;
}

/** The line under the first circuit: an employer only counts the rest. */
export function moreCircuitsLine(more: number, w: AssessWords): string {
  if (w.hiring) return `${more} more ${more === 1 ? w.circuit : w.circuits}`;
  return `${more} more ${w.circuits} · ${w.supervisors} see their own ${w.circuit} first`;
}

export const editLabel = (w: AssessWords): string => (w.hiring ? "Edit details" : "Edit");

export const cancelMenuLabel = (w: AssessWords): string => (w.hiring ? `Cancel this ${w.sitting}` : `Cancel ${w.sitting}`);

/** The cancel confirmation; an employer is told who hears of it. */
export function cancelMessage(w: AssessWords): string {
  const base = "Nobody can take it once it is cancelled. Nothing has started, so no attempt is lost.";
  return w.hiring ? `${base} Candidates and assessors are told by email.` : base;
}
