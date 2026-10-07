/** The attempts that have feedback to read: marked, and not a debrief conversation. Numbered in order. */
export function feedbackRows<T extends { has_result: boolean; kind: string }>(
  attempts: readonly T[],
): (T & { position: number })[] {
  return attempts
    .filter((item) => item.has_result && item.kind !== "debrief")
    .map((item, index) => ({ ...item, position: index + 1 }));
}
