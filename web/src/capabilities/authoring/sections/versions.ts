/**
 * Which version of a template or rubric is live, and which is being written.
 *
 * Every versioned thing here carries its whole version list, and every list
 * screen asks the same two questions of it. Asking them in one place is what
 * keeps "Live · v3" meaning the same thing in all five sections — in the
 * retiring client each tree worked it out again and they disagreed about
 * archived rows.
 */
export interface VersionLike {
  version: number;
  status: string;
}

export function latestOf<T extends VersionLike>(versions: readonly T[]): {
  published: T | null;
  draft: T | null;
  archivedOnly: boolean;
} {
  const newest = (matching: (v: T) => boolean) =>
    versions.filter(matching).sort((a, b) => b.version - a.version)[0] ?? null;

  const published = newest((v) => v.status === "published");
  const draft = newest((v) => v.status !== "published" && v.status !== "archived");
  const archivedOnly =
    versions.length > 0 && published === null && draft === null;

  return { published, draft, archivedOnly };
}

/**
 * Whether the viewer may publish, archive or delete a template. A platform template seen from
 * an organisation is theirs to copy, not to manage: every such call answers
 * `station_template_not_found`, so the row offers none of them.
 */
export function canManageTemplate(scopeKind: "org" | "platform", ownerKind: string): boolean {
  return !(scopeKind === "org" && ownerKind === "platform");
}
