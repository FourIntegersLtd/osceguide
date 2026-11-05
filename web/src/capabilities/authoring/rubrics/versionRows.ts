import { formatShortDate } from "@/foundation/format";
import type { RubricVersion } from "@/capabilities/authoring/api/scope";

type Tone = "success" | "warning" | "default";

export type VersionRow = { id: string; version: number; detail: string; chip: { label: string; tone: Tone } };

/** Newest first. A draft reads "Draft", the current version "Live", an archived one "Archived", any other published one "Old". */
export function versionRows(versions: readonly RubricVersion[], currentVersionId: string | null | undefined): VersionRow[] {
  const sorted = [...versions].sort((a, b) => b.version - a.version);
  return sorted.map((v) => {
    if (v.status === "draft") return { id: v.id, version: v.version, detail: "Draft", chip: { label: "Draft", tone: "warning" } };
    if (v.status === "archived") return { id: v.id, version: v.version, detail: "Archived", chip: { label: "Archived", tone: "default" } };
    const detail = v.published_at ? `Published ${formatShortDate(v.published_at)}` : "Published";
    return v.id === currentVersionId
      ? { id: v.id, version: v.version, detail, chip: { label: "Live", tone: "success" } }
      : { id: v.id, version: v.version, detail, chip: { label: "Old", tone: "default" } };
  });
}
