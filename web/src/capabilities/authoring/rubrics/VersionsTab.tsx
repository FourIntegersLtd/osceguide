"use client";

import { Badge } from "@/foundation/ui";
import type { RubricVersion } from "@/capabilities/authoring/api";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { versionRows } from "@/capabilities/authoring/rubrics/versionRows";

/** Every version of the scheme: open one, archive a published one, or start the next draft. */
export function VersionsTab({
  versions,
  current,
  open,
  owned,
  adding,
  onOpen,
  onArchive,
  onNewDraft,
  onDraftFrom,
}: {
  versions: readonly RubricVersion[];
  current: string | null | undefined;
  /** The version on screen. */
  open: number;
  owned: boolean;
  adding: boolean;
  onOpen: (version: number) => void;
  onArchive: (version: RubricVersion) => void;
  onNewDraft: () => void;
  onDraftFrom: (version: number) => void;
}) {
  const draft = versions.find((v) => v.status === "draft");
  return (
    <ul className="space-y-2" data-path="versions">
      {versionRows(versions, current).map((row) => {
        const full = versions.find((v) => v.id === row.id);
        return (
          <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 rounded-osce-md border border-osce-border px-3 py-2 text-osce-body text-ink">
            <span>
              <span className="font-medium">v{row.version}</span> <span className="text-osce-caption text-ink-muted">{row.detail}</span>
            </span>
            <span className="flex flex-wrap items-center gap-2">
              <Badge tone={row.chip.tone} size="sm" dot>{row.chip.label}</Badge>
              {row.version !== open ? <AuthoringButton variant="ghost" size="sm" onClick={() => onOpen(row.version)}>Open</AuthoringButton> : null}
              {owned ? <AuthoringButton variant="ghost" size="sm" isLoading={adding} onClick={() => onDraftFrom(row.version)}>New draft from this</AuthoringButton> : null}
              {owned && full?.status === "published" ? <AuthoringButton variant="ghost" size="sm" onClick={() => onArchive(full)}>Archive</AuthoringButton> : null}
            </span>
          </li>
        );
      })}
      {owned && !draft ? (
        <li>
          <AuthoringButton variant="secondary" size="sm" isLoading={adding} onClick={onNewDraft}>New draft version</AuthoringButton>
        </li>
      ) : null}
      {owned && draft && draft.version !== open ? (
        <li className="text-osce-caption text-ink-muted">A draft already exists (version {draft.version}); open it instead of starting another.</li>
      ) : null}
    </ul>
  );
}
