import { plural } from "@/foundation/format";
import { undecided } from "@/domains/assess/results/support";

/** The hire results list's words (docs/institution-overhaul/hire/boards/HireResults.dc.html). */
export const HIRE_RESULTS = {
  description: "Assessments with marking finished. Decide each candidate, then release their results.",
  emptyTitle: "No results yet",
  emptyBody: "Results appear here once assessors finish marking an assessment.",
  emptyLink: "See assessments",
  whereHeading: "Where it is",
} as const;

type WhereRow = {
  mode?: string;
  not_decided: number;
  draft: number;
  signed_off: number;
  released?: number;
  sat?: number;
};

/**
 * Where an assessment's results have got to, from the list row's own counts: still being marked,
 * decisions to make, decisions to sign off, or released. A training assessment records no
 * decisions, so its results go straight to the candidates.
 */
export function whereItIs(row: WhereRow): { label: string; tone: "ok" | "warn" | "neutral" } {
  if (row.mode === "training") return { label: "Released", tone: "ok" };
  const waiting = undecided(row);
  if (waiting > 0) return { label: plural(waiting, "decision") + " to make", tone: "warn" };
  if (row.draft > 0 || row.signed_off > 0) return { label: "Signed off, not released", tone: "warn" };
  if ((row.released ?? 0) > 0) return { label: "Released", tone: "ok" };
  return { label: "Marking", tone: "neutral" };
}
