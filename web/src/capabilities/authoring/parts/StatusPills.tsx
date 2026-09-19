"use client";

import type { ReactNode } from "react";

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
    <div className="mt-2 space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        {kindLabel ? (
          <span className="rounded-md bg-b2b-cream px-2 py-0.5 text-osce-caption font-medium text-b2b-mid">
            {kindLabel}
          </span>
        ) : null}
        {published ? (
          <Pill className="bg-b2b-success-bg text-b2b-success-text ring-b2b-success-border/40">
            Live · v{published.version}
          </Pill>
        ) : (
          <Pill className="bg-b2b-warning-bg text-b2b-warning-text ring-b2b-warning-border/40">
            Not live
          </Pill>
        )}
        {draft ? (
          <Pill className="bg-b2b-cream text-b2b-graphite ring-b2b-border">
            Draft · v{draft.version}
          </Pill>
        ) : null}
        {archivedOnly ? (
          <Pill className="bg-b2b-subtle text-b2b-graphite ring-b2b-border">Archived only</Pill>
        ) : null}
      </div>
    </div>
  );
}

function Pill({ className, children }: { className: string; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-osce-caption font-semibold ring-1 ${className}`}
    >
      {children}
    </span>
  );
}

const DRAFT_BADGE = { label: "Draft", className: "bg-b2b-cream text-b2b-graphite" };

const STATION_STATUS: Record<string, { label: string; className: string }> = {
  published: { label: "Published", className: "bg-b2b-success-bg text-b2b-success-text" },
  archived: { label: "Archived", className: "bg-b2b-subtle text-b2b-graphite" },
  draft: DRAFT_BADGE,
};

/** A version's own status, as the station rows showed it. */
export function StatusBadge({ status }: { status: string | undefined }) {
  const badge = STATION_STATUS[status ?? "draft"] ?? DRAFT_BADGE;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-osce-caption font-semibold ring-1 ring-b2b-border ${badge.className}`}
    >
      {badge.label}
    </span>
  );
}
