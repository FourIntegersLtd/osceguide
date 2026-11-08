/** The Decisions screen's hire-only rules and words, pure so they are tested (board HireDecisions). */
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import { plural } from "@/foundation/format";

/** A hiring decision belongs to an employer's formal exam; Training gives feedback only. */
export function showsHiringDecision(mode: string, w: AssessWords): boolean {
  return w.hiring && mode === "exam";
}

export function trainingNotice(mode: string, w: AssessWords): { title: string; body: string } | null {
  if (!w.hiring || mode === "exam") return null;
  return {
    title: `This was a ${w.training} ${w.sitting}`,
    body: `${w.training} gives ${w.trainees} feedback only, so there are no hiring decisions. Sign off and release the results as usual.`,
  };
}

interface Decidable {
  user_id?: string | null;
  trainee_id?: string | null;
  stations?: readonly { absent?: boolean }[];
  decision?: { recruitment_outcome?: string | null; signed_off_at?: string | null; signed_off_by_name?: string | null } | null;
}

/** Who a decision can be recorded for: on the roster, and sat at least one station (an absent candidate cannot be decided). */
export function decidable<T extends Decidable>(candidates: readonly T[]): T[] {
  return candidates.filter((candidate) => candidate.trainee_id != null && (!candidate.stations || candidate.stations.some((station) => !station.absent)));
}

/**
 * The next candidate after `currentId`, in the report's order, who can be decided and has no hiring decision yet (as hiringTally counts it);
 * the list wraps once so the ones before are not skipped. Null when nobody else is left.
 */
export function nextUndecided<T extends Decidable>(candidates: T[], currentId: string | null): T | null {
  const at = candidates.findIndex((candidate) => candidate.user_id === currentId);
  const ordered = [...candidates.slice(at + 1), ...candidates.slice(0, Math.max(at, 0))];
  return (
    decidable(ordered).find(
      (candidate) => candidate.user_id !== currentId && (!candidate.decision?.recruitment_outcome || candidate.decision.recruitment_outcome === "pending"),
    ) ?? null
  );
}

export function saveNextLabel(hasNext: boolean): string {
  return hasNext ? "Save and next candidate" : "Save decision";
}

/** "14 Oct": the day an assessment was held, in the reader's own time zone. */
export function shortDay(iso: string | null | undefined): string | null {
  const date = iso ? new Date(iso) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : null;
}

/** The line under an exam assessment's name on the decisions screen. */
export function hireResultsSubtitle(scheduledFor: string | null | undefined, candidates: number): string {
  const parts = ["Formal exam", shortDay(scheduledFor), plural(candidates, "candidate")].filter(Boolean);
  return `${parts.join(" · ")}. Decide each candidate, sign off, then release.`;
}

/** Why Sign off waits: every candidate needs a hiring decision first. Null once nobody is left. */
export function signOffGate(total: number, left: number): string | null {
  return left > 0 ? `Sign off needs a decision for all ${total} candidates. ${left} ${left === 1 ? "is" : "are"} left.` : null;
}

/**
 * Who signed the sheet off and when, once every candidate who can be decided is signed off (or released);
 * the latest signature, since each candidate carries their own. Null while anyone is unsigned.
 */
export function sheetSignature(candidates: readonly Decidable[]): { name: string | null; at: string } | null {
  const who = decidable(candidates);
  const signed = who.flatMap((candidate) => (candidate.decision?.signed_off_at ? [{ at: candidate.decision.signed_off_at, name: candidate.decision.signed_off_by_name ?? null }] : []));
  if (who.length === 0 || signed.length < who.length) return null;
  return signed.reduce((latest, next) => (Date.parse(next.at) > Date.parse(latest.at) ? next : latest));
}

/** "Signed off by Joy Okafor, today 14:02" (an earlier day reads "14 Oct 14:02"); the name is left out when unknown. */
export function signedOffByLine(signature: { name: string | null; at: string }, now: Date): string {
  const at = new Date(signature.at);
  const time = at.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const sameDay = at.toDateString() === now.toDateString();
  return `Signed off${signature.name ? ` by ${signature.name}` : ""}, ${sameDay ? "today" : shortDay(signature.at)} ${time}`;
}

export const SIGN_OFF_SHEET_LABEL = "Sign off results";

export const releaseResultsLabel = (count: number): string => `Release results to ${plural(count, "candidate")}`;

export const RELEASE_HELPER = "They get an email and can read their result and feedback. Hiring decisions are not sent.";

export function releasedSummary(total: number, tally: { hired: number; reserve: number; notHired: number }): string {
  return `${plural(total, "candidate")} ${total === 1 ? "has" : "have"} been told. Hired ${tally.hired} · Reserve list ${tally.reserve} · Not hired ${tally.notHired}.`;
}

/** A station's verdict from the marking; null while it has none. */
export const stationVerdict = (passed: boolean | null | undefined): "Pass" | "Fail" | null => (passed == null ? null : passed ? "Pass" : "Fail");

export const stationsPassedLine = (passed: number, total: number): string => `${passed} of ${plural(total, "station")} passed`;

/** Under the Result choice: what the marking says, and that overriding it needs a reason. */
export const resultOverrideHelper = (passed: number, total: number): string => `From the marking: ${stationsPassedLine(passed, total)}. Change it only with a reason.`;
