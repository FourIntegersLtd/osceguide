"use client";

import { useCallback, useMemo } from "react";
import { HiOutlineArchiveBox, HiOutlineChevronRight } from "react-icons/hi2";
import Table, {
  type FetchPageResult,
} from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import type { Station } from "@/capabilities/authoring/api";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { cn } from "@/foundation/ui/cn";

function stationCreatedAtLabel(station: Station): string {
  const raw = station.content?.created_at;
  const iso = typeof raw === "string" ? raw : null;
  if (!iso) return "—";
  const normalized = /[zZ]$/.test(iso) || /[+-]\d{2}/.test(iso) ? iso : `${iso}Z`;
  const date = new Date(normalized);
  if (!Number.isFinite(date.getTime())) return "—";
  return date.toLocaleString("en-GB");
}

function LegacyApprovalPill({ station }: { station: Station }) {
  const approved = station.content?.approved;
  if (typeof approved !== "boolean") return null;
  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 font-medium",
        b2cTableCellText,
        approved ? "bg-osce-success-bg text-osce-success-text" : "bg-osce-warning-bg text-osce-warning-text",
      )}
    >
      {approved ? "Approved" : "Pending"}
    </span>
  );
}

export function StationsTable({
  stations,
  search,
  busy,
  onOpen,
  onArchive,
}: {
  stations: Station[];
  search: string;
  busy: string | null;
  onOpen: (station: Station) => void;
  onArchive?: (station: Station) => void;
}) {
  // Every row loaded so far, with the table's own pager off: paging is the
  // server's cursor (Load more), and filtering already happened in SQL.
  const fetchPage = useCallback(
    async (): Promise<FetchPageResult<Station>> => ({ items: stations, totalCount: stations.length }),
    [stations],
  );

  const columns = useMemo(
    () => [
      {
        header: "Station name",
        key: "title" as keyof Station,
        priority: "primary" as const,
        render: (station: Station) => (
          <button
            type="button"
            onClick={() => onOpen(station)}
            className={cn(b2cTableCellText, "text-left font-medium text-osce-ink-900 hover:text-osce-accent")}
          >
            {station.title}
          </button>
        ),
      },
      {
        header: "Exam",
        key: "exam_code" as keyof Station,
        render: (station: Station) => (
          <span className={cn(b2cTableCellText, "rounded-full bg-osce-accent-subtle px-3 py-1 text-osce-accent-hover")}>
            {station.exam_code.toUpperCase()}
          </span>
        ),
      },
      {
        header: "Status",
        key: "status" as keyof Station,
        render: (station: Station) => (
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={station.status} />
            <LegacyApprovalPill station={station} />
          </div>
        ),
      },
      {
        header: "Created at",
        key: "id" as keyof Station,
        className: "hidden lg:table-cell",
        priority: "detail" as const,
        render: (station: Station) => (
          <span className={cn(b2cTableCellText, "text-b2c-text-muted")}>{stationCreatedAtLabel(station)}</span>
        ),
      },
      {
        header: "Actions",
        key: "version" as keyof Station,
        priority: "detail" as const,
        render: (station: Station) => {
          const archiveBusy = busy === `archive:${station.id}`;
          const canArchive = station.status === "published" && onArchive;
          return (
            <AuthoringRowActions>
              {canArchive ? (
                <AuthoringIconAction
                  variant="warning"
                  label="Archive"
                  busy={archiveBusy}
                  busyLabel="Archiving…"
                  disabled={busy !== null}
                  onClick={() => onArchive(station)}
                >
                  <HiOutlineArchiveBox className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
              <AuthoringIconAction variant="ghost" label="Open versions" onClick={() => onOpen(station)}>
                <HiOutlineChevronRight className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
            </AuthoringRowActions>
          );
        },
      },
    ],
    [busy, onArchive, onOpen],
  );

  return (
    <Table<Station>
      fetchPage={fetchPage}
      showPagination={false}
      columns={columns}
      idField="id"
      nameField="title"
      search={search}
      showSearch={false}
    />
  );
}
