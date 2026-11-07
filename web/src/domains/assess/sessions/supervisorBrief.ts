import type { StaffSection } from "@/domains/assess/sessions/api";

/** Blocks the server holds for one audience whatever section they are filed in. */
const HELD_ROLES = new Set(["hidden", "examiner", "faculty", "debrief"]);

/**
 * What the supervisor console shows of a station: the candidate's own brief and nothing else.
 *
 * The server is asked for the candidate audience only; this keeps the screen right even if a
 * wider read ever reaches it. Patient, hidden, examiner and faculty material never gets through.
 */
export function candidateSections(sections: readonly StaffSection[]): StaffSection[] {
  return sections
    .filter((section) => section.audience === "candidate")
    .map((section) => ({ ...section, blocks: section.blocks.filter((block) => !HELD_ROLES.has(block.role)) }))
    .filter((section) => section.blocks.length > 0);
}

/**
 * An untemplated station's candidate brief: `reading_brief`, else the older `candidate_brief`
 * (the server's `stations.domain_content.BRIEF_KEYS`). Every other field is withheld.
 */
export function untemplatedBrief(content: Record<string, unknown>): string | null {
  for (const key of ["reading_brief", "candidate_brief"]) {
    const value = content[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}
