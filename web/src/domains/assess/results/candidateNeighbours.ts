/**
 * Where a station review sits among the candidates who took the same station.
 *
 * There is no "next candidate" route. The sitting's report already lists every
 * candidate with their stations, so the neighbours are read off it: the same
 * station, for the candidate before and after in the report's order.
 */
interface StepStation {
  slot_id: string;
  attempt_id: string | null;
  circuit_id: string;
  slot_index: number;
  circuit_name?: string;
  station_title?: string | null;
}

interface StepCandidate {
  name: string | null;
  stations?: StepStation[];
}

export interface CandidateStep {
  slotId: string;
  attemptId: string | null;
  name: string | null;
}

export interface CandidateSteps {
  /** One-based, among the candidates who have this station. */
  position: number;
  total: number;
  previous: CandidateStep | null;
  next: CandidateStep | null;
}

/** A station review's address, carrying the sitting it was opened from. */
export function reviewPath(slotId: string, attemptId: string | null | undefined, sittingId: string): string {
  const query = new URLSearchParams();
  if (attemptId) query.set("attempt", attemptId);
  query.set("sitting", sittingId);
  return `/slots/${slotId}/review?${query.toString()}`;
}

/**
 * A slot belongs to one candidate, so the same station for the next candidate is the slot at the
 * same place in the same circuit, not the same title (two stations can share a title, or have none).
 */
export function candidateSteps(candidates: StepCandidate[], slotId: string): CandidateSteps | null {
  const here = candidates.flatMap((candidate) => candidate.stations ?? []).find((station) => station.slot_id === slotId);
  if (!here) return null;
  const steps: CandidateStep[] = [];
  for (const candidate of candidates) {
    const station = (candidate.stations ?? []).find(
      (entry) => entry.circuit_id === here.circuit_id && entry.slot_index === here.slot_index,
    );
    if (station) steps.push({ slotId: station.slot_id, attemptId: station.attempt_id, name: candidate.name });
  }
  const index = steps.findIndex((step) => step.slotId === slotId);
  if (index === -1) return null;
  return {
    position: index + 1,
    total: steps.length,
    previous: steps[index - 1] ?? null,
    next: steps[index + 1] ?? null,
  };
}

/** Who and what a station review is of, for its back link and eyebrow ("Circuit 1 · Amara Okoye", "Amara Okoye · Station 2 · Breaking bad news"). */
export function slotContext(candidates: StepCandidate[], slotId: string): { back: string; eyebrow: string } | null {
  for (const candidate of candidates) {
    const station = (candidate.stations ?? []).find((entry) => entry.slot_id === slotId);
    if (!station) continue;
    const who = candidate.name ?? "Candidate";
    const circuit = station.circuit_name ? `${station.circuit_name} · ${who}` : who;
    const title = station.station_title ? ` · ${station.station_title}` : "";
    return { back: circuit, eyebrow: `${who} · Station ${station.slot_index + 1}${title}` };
  }
  return null;
}
