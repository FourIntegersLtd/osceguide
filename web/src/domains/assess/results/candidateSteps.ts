/**
 * Where a station review sits among the candidates who took the same station.
 *
 * There is no "next candidate" route. The sitting's report already lists every
 * candidate with their stations, so the neighbours are read off it: the same
 * station, by title, for the candidate before and after in the report's order.
 */
interface StepStation {
  slot_id: string;
  attempt_id: string | null;
  station_title: string | null;
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

export function candidateSteps(candidates: StepCandidate[], slotId: string): CandidateSteps | null {
  const title = candidates
    .flatMap((candidate) => candidate.stations ?? [])
    .find((station) => station.slot_id === slotId)?.station_title;
  // An untitled station cannot be matched to anybody else's.
  if (!title) return null;

  const steps: CandidateStep[] = [];
  for (const candidate of candidates) {
    const station = (candidate.stations ?? []).find((entry) => entry.station_title === title);
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
