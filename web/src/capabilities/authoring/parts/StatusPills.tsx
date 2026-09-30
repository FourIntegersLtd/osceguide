"use client";

import { Badge, type BadgeTone } from "@/foundation/ui";

/**
 * The publish state of a versioned thing, in the words the old screens used.
 *
 * "Live · v3" and "Not live" rather than the backend's `published` /`draft`:
 * an author asks whether candidates are seeing it, and the answer to that is
 * not the same sentence as the row's status column.
 */
export function PublishStatusLine({
  kindLabel,
  published,
  draft,
  archivedOnly,
}: {
  kindLabel?: string | null;
  published?: { version: number } | null;
  draft?: { version: number } | null;
  archivedOnly?: boolean;
}) {
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
      {kindLabel ? (
        <Badge tone="neutral" size="xs">
          {kindLabel}
        </Badge>
      ) : null}
      {published ? (
        <Badge tone="success" size="sm" dot>
          Live · v{published.version}
        </Badge>
      ) : (
        <Badge tone="warning" size="sm" dot>
          Not live
        </Badge>
      )}
      {draft ? (
        <Badge tone="neutral" size="sm">
          Draft · v{draft.version}
        </Badge>
      ) : null}
      {archivedOnly ? (
        <Badge tone="default" size="sm">
          Archived only
        </Badge>
      ) : null}
    </div>
  );
}

const DRAFT_BADGE = { label: "Draft", tone: "warning" as const };

const ROW_STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  published: { label: "Published", tone: "success" },
  active: { label: "Active", tone: "success" },
  draft: DRAFT_BADGE,
  retired: { label: "Retired", tone: "default" },
  archived: { label: "Archived", tone: "default" },
};

/** A row's own status — published, draft, retired, archived, or active. */
export function StatusBadge({ status }: { status: string | undefined }) {
  const badge = ROW_STATUS[status ?? "draft"] ?? DRAFT_BADGE;
  return (
    <Badge tone={badge.tone} size="sm" dot>
      {badge.label}
    </Badge>
  );
}
