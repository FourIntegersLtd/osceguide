"use client";

import { useMemo } from "react";
import { HiOutlineChevronRight, HiOutlineTrash } from "react-icons/hi2";
import Table, { type TableMore } from "@/foundation/table/Table";
import { Badge } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import type { MediaItem } from "@/capabilities/staff-media/api";

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
}: {
  items: MediaItem[];
  /** The "Load more" footer: the screen's cursor pages. */
  more: TableMore;
  busy: string | null;
  onOpen: (item: MediaItem) => void;
  onPublish: (item: MediaItem) => void;
  onDelete: (item: MediaItem) => void;
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
        render: (item: MediaItem) => (
          <Badge tone={item.status === "published" ? "success" : "warning"}>
            {item.status === "published" ? "Published" : "Draft"}
          </Badge>
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
              {isDraft ? (
                <AuthoringIconAction
                  variant="primary"
                  label="Publish"
                  busy={busy === `publish:${item.id}`}
                  busyLabel="Publishing…"
                  disabled={busy !== null}
                  onClick={() => onPublish(item)}
                >
                  Publish
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
    [busy, onDelete, onOpen, onPublish],
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
