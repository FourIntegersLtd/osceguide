import type { PracticeSession } from "../api";
export type RunnerPhase = "loading" | "waiting_partner" | "preparation" | "consultation" | "debrief" | "completed" | "ended";
export function mapPhase(session: PracticeSession | null): RunnerPhase {
  if (!session) return "loading";
  if (session.current_phase === "completed") return "completed";
  if (["ended", "abandoned", "cancelled"].includes(session.status) || session.ended_at) return "ended";
  if (session.current_phase === "consultation" || session.current_phase === "debrief") return session.current_phase;
  if (session.current_phase === "preparation" || session.preparation_started_at) return "preparation";
  return "waiting_partner";
}
/** The session header's caption, under the clock and after the role. */
export function phaseLabel(phase: RunnerPhase): string {
  if (phase === "consultation") return "Simulation";
  if (phase === "debrief") return "Debrief";
  // Shown behind the "Session no longer available" and partner-left modals,
  // and for the moment before the feedback page takes over.
  if (phase === "ended" || phase === "completed") return "Ended";
  return "Reading";
}

/** The session header's title. */
export function phaseTitle(phase: RunnerPhase): string {
  if (phase === "debrief") return "Debrief";
  if (phase === "consultation") return "Live Consultation";
  if (phase === "ended" || phase === "completed") return "Session Ended";
  return "Preparation Phase";
}
const ranks: Record<RunnerPhase, number> = { loading: 0, waiting_partner: 1, preparation: 2, consultation: 3, debrief: 4, completed: 5, ended: 6 };
/** Both waiting states map to `waiting_partner`; an accepted match is still later than an unanswered one. */
function rank(session: PracticeSession): number {
  return ranks[mapPhase(session)] * 2 + (session.status === "pending_accept" ? 0 : 1);
}
/** A delayed read or retained SSE frame must never rewind the session. */
export function latestSession(id: string, ...snapshots: (PracticeSession | null | undefined)[]): PracticeSession | null {
  return snapshots.reduce<PracticeSession | null>((latest, candidate) => {
    if (!candidate || candidate.id !== id) return latest;
    return !latest || rank(candidate) >= rank(latest) ? candidate : latest;
  }, null);
}
export function remainingSeconds(endsAt: string | null | undefined, now: number): number | null {
  if (!endsAt) return null;
  const end = Date.parse(endsAt);
  return Number.isFinite(end) ? Math.max(0, Math.ceil((end - now) / 1000)) : null;
}

/** The `end` reason sent when leaving throws the consultation away. */
export const ABANDONED_REASON = "abandoned";

/**
 * Whether ending now abandons the session rather than completing it: before
 * the consultation starts, or with more than three minutes of it left. An
 * abandoned session sends the leaver to the dashboard and offers the partner
 * a requeue; any later end goes to feedback. The retiring client's rule.
 */
export function endingAbandons(phase: RunnerPhase, remaining: number | null): boolean {
  if (phase === "waiting_partner" || phase === "preparation") return true;
  return phase === "consultation" && (remaining ?? 0) > 180;
}

/** Why a partner is no longer there, in the words of the requeue modal. */
export type PartnerGone = "partner_left" | "no_response";

/** Where an ended session sends the person looking at it. */
export type SessionExit =
  | { kind: "stay" }
  | { kind: "feedback" }
  | { kind: "dashboard" }
  | { kind: "partner_gone"; reason: PartnerGone }
  | { kind: "requeued"; entryId: string };

const NO_RESPONSE_REASONS = new Set(["declined", "no_response"]);
const PARTNER_LEFT_REASONS = new Set([ABANDONED_REASON, "partner_left", "cancelled"]);

/**
 * Decide what an ended session does next. A match that fell through after
 * this side accepted is already requeued; only an early end offers the other
 * person a requeue; the one who ended it early goes to the dashboard; every
 * other ending, whoever pressed the button, goes to the feedback page.
 */
export function sessionExit(session: PracticeSession | null, endedByMe: boolean): SessionExit {
  const phase = mapPhase(session);
  if (phase === "completed") return { kind: "feedback" };
  if (phase !== "ended" || !session) return { kind: "stay" };
  const reason = session.end_reason ?? "";
  const noResponse = session.status === "cancelled" || NO_RESPONSE_REASONS.has(reason);
  // The partner declined or never answered after this side accepted: the
  // server has already put this side back in the queue.
  if (noResponse && session.requeued_entry_id) return { kind: "requeued", entryId: session.requeued_entry_id };
  if (noResponse || PARTNER_LEFT_REASONS.has(reason)) {
    return endedByMe ? { kind: "dashboard" } : { kind: "partner_gone", reason: noResponse ? "no_response" : "partner_left" };
  }
  return { kind: "feedback" };
}
