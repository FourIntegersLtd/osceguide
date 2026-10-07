"use client";

import { useMemo } from "react";
import {
  HiOutlineArrowDownTray,
  HiOutlineArrowUpTray,
  HiOutlineLockOpen,
  HiOutlineChevronRight,
  HiOutlineTrash,
} from "react-icons/hi2";
import Table, { type TableMore } from "@/foundation/table/Table";
import { Badge } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import type { MediaItem } from "@/capabilities/staff-media/api";
import {
  isSpokenKind,
} from "@/capabilities/staff-media/content/review";
import { avStatus, isAvRunning } from "@/capabilities/staff-media/content/b2cMediaShapes";
import {
  stageOf,
} from "@/capabilities/staff-media/content/steps";

function mediaDateLabel(iso: string | null | undefined): string {
  if (!iso) return "-";
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return "-";
  return date.toLocaleString("en-GB");
}

export function MediaListTable({
  items,
  more,
  busy,
  onOpen,
  onPublish,
  onDelete,
  onUnpublish,
  onUnlock,
}: {
  items: MediaItem[];
  /** The "Load more" footer: the screen's cursor pages. */
  more: TableMore;
  busy: string | null;
  onOpen: (item: MediaItem) => void;
  onPublish: (item: MediaItem) => void;
  onDelete: (item: MediaItem) => void;
  onUnpublish: (item: MediaItem) => void;
  onUnlock: (item: MediaItem) => void;
}) {
  const columns = useMemo(
    () => [
      {
        header: "Title",
        key: "title" as keyof MediaItem,
        priority: "primary" as const,
        render: (item: MediaItem) => (
          <button
            type="button"
            onClick={() => onOpen(item)}
            className={cn(
              b2cTableCellText,
              "text-left font-medium text-ink hover:text-accent",
            )}
          >
            {item.title}
          </button>
        ),
      },
      {
        header: "Exam",
        key: "exam_code" as keyof MediaItem,
        render: (item: MediaItem) => (
          <Badge tone="accent">{(item.exam_code ?? "-").toUpperCase()}</Badge>
        ),
      },
      {
        header: "Status",
        key: "status" as keyof MediaItem,
        render: (item: MediaItem) =>
          item.status === "published" ? (
            <Badge tone="success">Published</Badge>
          ) : (
            <span className="flex flex-col items-start gap-1">
              <Badge tone="warning">Draft</Badge>
              {/* Where a spoken draft stands in its pipeline, so the list says what needs staff. */}
              {item.content && isSpokenKind(item.kind) ? (
                <span className={cn(b2cTableCellText, "text-osce-meta text-ink-subtle")}>
                  {stageOf(item.kind, item.content)}
                </span>
              ) : null}
            </span>
          ),
      },
      {
        header: "Created",
        key: "created_at" as keyof MediaItem,
        className: "hidden lg:table-cell",
        priority: "detail" as const,
        render: (item: MediaItem) => (
          <span className={cn(b2cTableCellText, "text-ink-subtle")}>
            {mediaDateLabel(item.created_at)}
          </span>
        ),
      },
      {
        header: "Actions",
        key: "id" as keyof MediaItem,
        priority: "detail" as const,
        render: (item: MediaItem) => {
          const isDraft = item.status === "draft";
          const running = isAvRunning(avStatus(item.content ?? {}));
          return (
            <AuthoringRowActions>
              {isDraft ? (
                <AuthoringIconAction
                  variant="ghost"
                  label="Delete draft"
                  busy={busy === `delete:${item.id}`}
                  busyLabel="Deleting…"
                  disabled={busy !== null}
                  onClick={() => onDelete(item)}
                >
                  <HiOutlineTrash className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
              {running ? (
                <AuthoringIconAction
                  variant="ghost"
                  label="Release stuck job"
                  busy={busy === `unlock:${item.id}`}
                  busyLabel="Releasing…"
                  disabled={busy !== null}
                  onClick={() => onUnlock(item)}
                >
                  <HiOutlineLockOpen className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
              {!isDraft ? (
                <AuthoringIconAction
                  variant="ghost"
                  label="Unpublish"
                  busy={busy === `unpublish:${item.id}`}
                  busyLabel="Unpublishing…"
                  disabled={busy !== null}
                  onClick={() => onUnpublish(item)}
                >
                  <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
              {isDraft && !running ? (
                <AuthoringIconAction
                  variant="primary"
                  label="Publish"
                  busy={busy === `publish:${item.id}`}
                  busyLabel="Publishing…"
                  disabled={busy !== null}
                  onClick={() => onPublish(item)}
                >
                  <HiOutlineArrowUpTray className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
              <AuthoringIconAction
                variant="ghost"
                label="Edit"
                onClick={() => onOpen(item)}
              >
                <HiOutlineChevronRight className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
            </AuthoringRowActions>
          );
        },
      },
    ],
    [busy, onDelete, onOpen, onPublish, onUnlock, onUnpublish],
  );

  return (
    <Table<MediaItem>
      rows={items}
      more={more}
      columns={columns}
      idField="id"
    />
  );
}
