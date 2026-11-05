import { formatShortDate } from "@/foundation/format";
import type { RubricVersion } from "@/capabilities/authoring/api/scope";

type Tone = "success" | "warning" | "default";

export type VersionRow = { id: string; version: number; detail: string; chip: { label: string; tone: Tone } };

function editedWhen(iso: string | null | undefined, now: Date): string {
  if (!iso) return "Draft";
  const at = new Date(iso);
  const today = at.getFullYear() === now.getFullYear() && at.getMonth() === now.getMonth() && at.getDate() === now.getDate();
  return `Draft, edited ${today ? "today" : formatShortDate(iso)}`;
}

/**
 * Newest first. A draft reads "Draft, edited today", the current version "Live", an archived one
 * "Archived {date}", any other published one "Old"; a published row names the exams that use it.
 */
export function versionRows(
  versions: readonly RubricVersion[],
  currentVersionId: string | null | undefined,
  now: Date = new Date(),
): VersionRow[] {
  const sorted = [...versions].sort((a, b) => b.version - a.version);
  return sorted.map((v) => {
    if (v.status === "draft") return { id: v.id, version: v.version, detail: editedWhen(v.updated_at, now), chip: { label: "Draft", tone: "warning" } };
    if (v.status === "archived") return { id: v.id, version: v.version, detail: v.archived_at ? `Archived ${formatShortDate(v.archived_at)}` : "Archived", chip: { label: "Archived", tone: "default" } };
    const published = v.published_at ? `Published ${formatShortDate(v.published_at)}` : "Published";
    const used = v.used_by_exams?.length ? ` · used by ${v.used_by_exams.join(", ")}` : "";
    const detail = published + used;
    return v.id === currentVersionId
      ? { id: v.id, version: v.version, detail, chip: { label: "Live", tone: "success" } }
      : { id: v.id, version: v.version, detail, chip: { label: "Old", tone: "default" } };
  });
}
