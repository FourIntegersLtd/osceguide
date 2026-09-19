import type { TutorNote } from "@/capabilities/account/api";

/**
 * A note as a sentence somebody can read.
 *
 * `body` is an open JSON object because the tutor's note kinds genuinely
 * differ — a weakness names a domain, a preference names a habit — and the
 * backend is free to add one. Narrowing here rather than casting at the point
 * of use means a kind this build has never seen renders its own words instead
 * of throwing on a screen whose whole purpose is showing you what is held.
 */
export function noteSentence(note: TutorNote): string {
  const body = note.body as Record<string, unknown>;
  for (const key of ["summary", "text", "note", "body", "content", "statement"]) {
    const value = body[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  const strings = Object.values(body).filter(
    (value): value is string => typeof value === "string" && value.trim().length > 0,
  );
  return strings.length > 0 ? strings.join(" · ") : "A note with nothing readable in it.";
}
