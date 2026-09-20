"use client";

import { useCallback, useMemo } from "react";
import { HiOutlineChevronRight, HiOutlineTrash } from "react-icons/hi2";
import Table, { type FetchPageParams, type FetchPageResult } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { matchesExamFilter } from "@/capabilities/authoring/parts/examCatalogFilter";
import type { MediaItem } from "@/capabilities/staff-media/api";

function mediaDateLabel(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return "—";
  return date.toLocaleString("en-GB");
}

function StatusPill({ status }: { status: string }) {
  const published = status === "published";
  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 font-medium",
        b2cTableCellText,
        published ? "bg-osce-success-bg text-osce-success-text" : "bg-osce-warning-bg text-osce-warning-text",
      )}
    >
      {published ? "Published" : "Draft"}
    </span>
  );
}

export function MediaListTable({
  items,
  examFilter,
  search,
  busy,
  onOpen,
  onPublish,
  onDelete,
}: {
  items: MediaItem[];
  examFilter: string;
  search: string;
  busy: string | null;
  onOpen: (item: MediaItem) => void;
  onPublish: (item: MediaItem) => void;
  onDelete: (item: MediaItem) => void;
}) {
  const pool = useMemo(
    () => items.filter((item) => matchesExamFilter(item.exam_code, examFilter)),
    [items, examFilter],
  );

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<MediaItem>> => {
      let filtered = pool;
      if (params.search) {
        const q = params.search.toLowerCase();
        filtered = pool.filter(
          (item) =>
            item.title.toLowerCase().includes(q) ||
            item.slug.toLowerCase().includes(q) ||
            (item.exam_code ?? "").toLowerCase().includes(q),
        );
      }
      const start = (params.page - 1) * params.perPage;
      const end = start + params.perPage;
      return { items: filtered.slice(start, end), totalCount: filtered.length };
    },
    [pool],
  );

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
            className={cn(b2cTableCellText, "text-left font-medium text-osce-ink-900 hover:text-osce-accent")}
          >
            {item.title}
          </button>
        ),
      },
      {
        header: "Exam",
        key: "exam_code" as keyof MediaItem,
        render: (item: MediaItem) => (
          <span className={cn(b2cTableCellText, "rounded-full bg-osce-accent-subtle px-3 py-1 text-osce-accent-hover")}>
            {(item.exam_code ?? "—").toUpperCase()}
          </span>
        ),
      },
      {
        header: "Status",
        key: "status" as keyof MediaItem,
        render: (item: MediaItem) => <StatusPill status={item.status} />,
      },
      {
        header: "Created",
        key: "created_at" as keyof MediaItem,
        className: "hidden lg:table-cell",
        priority: "detail" as const,
        render: (item: MediaItem) => (
          <span className={cn(b2cTableCellText, "text-b2c-text-muted")}>
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
              <AuthoringIconAction variant="ghost" label="Edit" onClick={() => onOpen(item)}>
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
      fetchPage={fetchPage}
      columns={columns}
      idField="id"
      nameField="title"
      search={search}
      showSearch={false}
    />
  );
}
