/**
 * How the product spells the reasons an attempt happened.
 *
 * The backend's `attempts.Kind`, which is one table and one vocabulary for
 * what the retiring clients called a practice, a mock station, a debrief and
 * an exam slot. An unknown kind shows its own word rather than nothing, so a
 * kind added on the server is readable here before anybody edits this file.
 */
const KIND_LABELS: Record<string, string> = {
  practice: "Practice",
  set_station: "Mock station",
  debrief: "Debrief",
  self_practice: "Self practice",
  exam_slot: "Exam station",
  peer: "Peer session",
};

export function attemptKindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind.replace(/_/g, " ");
}
