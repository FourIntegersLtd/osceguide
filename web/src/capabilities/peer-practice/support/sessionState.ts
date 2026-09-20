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
const ranks: Record<RunnerPhase, number> = { loading: 0, waiting_partner: 1, preparation: 2, consultation: 3, debrief: 4, completed: 5, ended: 6 };
/** A delayed read or retained SSE frame must never rewind the session. */
export function latestSession(id: string, ...snapshots: (PracticeSession | null | undefined)[]): PracticeSession | null {
  return snapshots.reduce<PracticeSession | null>((latest, candidate) => {
    if (!candidate || candidate.id !== id) return latest;
    return !latest || ranks[mapPhase(candidate)] >= ranks[mapPhase(latest)] ? candidate : latest;
  }, null);
}
export function remainingSeconds(endsAt: string | null | undefined, now: number): number | null {
  if (!endsAt) return null;
  const end = Date.parse(endsAt);
  return Number.isFinite(end) ? Math.max(0, Math.ceil((end - now) / 1000)) : null;
}
