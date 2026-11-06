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

export interface OlderPublished {
  version: number;
  exams: readonly string[];
  /** "A, B and C" */
  names: string;
  /** Exactly one exam is on it, so the sentence says "it" and "marks". */
  single: boolean;
}

/** The newest other published version that exams still mark with: a publish of `current` leaves them there until pointed over. */
export function olderPublished(versions: readonly RubricVersion[], current: number): OlderPublished | null {
  const older = versions.filter((v) => v.status === "published" && v.version !== current && v.used_by_exams?.length).sort((a, b) => b.version - a.version)[0];
  const exams = older?.used_by_exams ?? [];
  if (!older || exams.length === 0) return null;
  const names = exams.length > 1 ? `${exams.slice(0, -1).join(", ")} and ${exams[exams.length - 1]}` : (exams[0] ?? "");
  return { version: older.version, exams, names, single: exams.length === 1 };
}
