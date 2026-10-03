import type { AttemptPhase } from "@/capabilities/attempt-runner/useAttemptSession";

/**
 * Whether the consultation clock runs, and what it says while held.
 *
 * It runs only while the room is live and the patient is in it. Gating on the
 * patient alone kept it counting after "End consultation", because the patient
 * having joined stays true (staging, 2026-10-03).
 */
export function consultationClock(
  phase: AttemptPhase,
  patientJoined: boolean,
): { running: boolean; stoppedLabel: string } {
  const over = phase === "ending" || phase === "ended";
  return {
    running: phase === "live" && patientJoined,
    stoppedLabel: over ? "Consultation ended" : "Starts with the patient",
  };
}
