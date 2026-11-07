/**
 * Proposing the rotations of a formal exam. Each candidate's rotation is their own circuit, so the
 * thing to decide is who assesses it. The api keeps no start time per circuit, so none is proposed.
 */

/** Candidates dealt to the chosen assessors in turn, so the load is as even as it can be. */
export function proposeRotations(candidateIds: readonly string[], assessorIds: readonly string[]): Record<string, string> {
  if (assessorIds.length === 0) return {};
  return Object.fromEntries(candidateIds.map((id, at) => [id, assessorIds[at % assessorIds.length] as string]));
}

/** How many candidates each assessor has (in the order `names` lists them), and how many have nobody. */
export function assessorTally(
  candidateIds: readonly string[],
  byCandidate: Record<string, string>,
  names: Record<string, string>,
): { perAssessor: { id: string; name: string; count: number }[]; unassigned: number } {
  const counts = new Map<string, number>();
  let unassigned = 0;
  for (const id of candidateIds) {
    const assessor = byCandidate[id];
    if (assessor) counts.set(assessor, (counts.get(assessor) ?? 0) + 1);
    else unassigned += 1;
  }
  const perAssessor = Object.keys(names)
    .filter((id) => counts.has(id))
    .map((id) => ({ id, name: names[id] as string, count: counts.get(id) as number }));
  return { perAssessor, unassigned };
}

/** "Dan Lowe: 4 · Sara Khan: 3 · 1 with nobody yet": who has how many rotations. */
export function tallyText(tally: ReturnType<typeof assessorTally>): string {
  const parts = tally.perAssessor.map((row) => `${row.name}: ${row.count}`);
  if (tally.unassigned > 0) parts.push(`${tally.unassigned} with nobody yet`);
  return parts.join(" · ");
}
