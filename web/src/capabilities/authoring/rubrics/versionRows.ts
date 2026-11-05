import { formatShortDate } from "@/foundation/format";
import type { RubricVersion } from "@/capabilities/authoring/api/scope";

type Tone = "success" | "warning" | "default";

export type VersionRow = { id: string; version: number; detail: string; chip: { label: string; tone: Tone } };

/** Newest first. A draft reads "Draft", the newest published one "Live", every older one "Old". */
export function versionRows(versions: readonly RubricVersion[]): VersionRow[] {
  const sorted = [...versions].sort((a, b) => b.version - a.version);
  const liveId = sorted.find((v) => v.status === "published")?.id;
  return sorted.map((v) => {
    if (v.status === "draft") return { id: v.id, version: v.version, detail: "Draft", chip: { label: "Draft", tone: "warning" } };
    const detail = v.published_at ? `Published ${formatShortDate(v.published_at)}` : "Published";
    return v.id === liveId
      ? { id: v.id, version: v.version, detail, chip: { label: "Live", tone: "success" } }
      : { id: v.id, version: v.version, detail, chip: { label: "Old", tone: "default" } };
  });
}
