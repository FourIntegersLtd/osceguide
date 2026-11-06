"use client";

import { useMemo } from "react";
import { READER_EMPTY_TEXT } from "@/capabilities/authoring/parts/CannotAuthor";
import { HiOutlineArchiveBox, HiOutlineCheckBadge, HiOutlineChevronRight, HiOutlineXCircle } from "react-icons/hi2";
import Table, { type TableMore } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import type { Station } from "@/capabilities/authoring/api";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { usedByCell } from "@/capabilities/authoring/sections/StationUsedBy";
import { cn } from "@/foundation/ui/cn";
import { BoardChip, boardMeta } from "@/capabilities/authoring/parts/boardUi";
import { boardCardClipped, boardRowWide, boardHeadRowWide, boardPadWide, boardButtonSmall } from "@/foundation/ui/boardKit";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";

function stationCreatedAtLabel(station: Station, short = false): string {
  const raw = station.content?.created_at;
  const iso = typeof raw === "string" ? raw : null;
  if (!iso) return "-";
  const normalized = /[zZ]$/.test(iso) || /[+-]\d{2}/.test(iso) ? iso : `${iso}Z`;
  const date = new Date(normalized);
  if (!Number.isFinite(date.getTime())) return "-";
  return short ? date.toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" }) : date.toLocaleString("en-GB");
}

/** Whether an editor has signed a published station into the library. A draft has nothing to approve. */
function ApprovalPill({ station }: { station: Station }) {
  if (station.status !== "published") return null;
  return (
    <span
      className={cn(
        "rounded-full px-3 py-1 font-medium",
        b2cTableCellText,
        station.approved ? "bg-osce-success-bg text-osce-success-text" : "bg-osce-warning-bg text-osce-warning-text",
      )}
    >
      {station.approved ? "Approved" : "Awaiting approval"}
    </span>
  );
}

export function StationsTable({
  stations,
  more,
  search,
  busy,
  onOpen,
  onArchive,
  onToggleApproval,
}: {
  stations: Station[];
  /** The "Load more" footer: the section's cursor pages. */
  more: TableMore;
  search: string;
  busy: string | null;
  onOpen: (station: Station) => void;
  onArchive: (station: Station) => void;
  /** Staff only: approve a published station into the library, or take it back out. */
  onToggleApproval?: (station: Station) => void;
}) {
  const canAuthor = useCanAuthor();
  const org = !useAuthoringChrome().b2c;
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
            className={cn(b2cTableCellText, "text-left font-medium text-ink hover:text-osce-accent")}
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
            <ApprovalPill station={station} />
          </div>
        ),
      },
      {
        header: "Used by",
        key: "used_by_count" as keyof Station,
        priority: "secondary" as const,
        render: (station: Station) => (
          <span className={cn(b2cTableCellText, "text-ink-subtle")}>{usedByCell(station.used_by_count)}</span>
        ),
      },
      {
        header: "Created at",
        key: "id" as keyof Station,
        className: "hidden lg:table-cell",
        priority: "detail" as const,
        render: (station: Station) => (
          <span className={cn(b2cTableCellText, "text-ink-subtle")}>{stationCreatedAtLabel(station)}</span>
        ),
      },
      {
        header: "Actions",
        key: "version" as keyof Station,
        priority: "detail" as const,
        render: (station: Station) => {
          const archiveBusy = busy === `archive:${station.id}`;
          const canArchive = station.status === "published";
          const approvalBusy = busy === `approval:${station.id}`;
          return (
            <AuthoringRowActions>
              {onToggleApproval && canArchive ? (
                <AuthoringIconAction
                  write
                  variant="ghost"
                  label={station.approved ? "Withdraw approval" : "Approve"}
                  busy={approvalBusy}
                  busyLabel={station.approved ? "Withdrawing…" : "Approving…"}
                  disabled={busy !== null}
                  onClick={() => onToggleApproval(station)}
                >
                  {station.approved ? (
                    <HiOutlineXCircle className="h-4 w-4" aria-hidden />
                  ) : (
                    <HiOutlineCheckBadge className="h-4 w-4" aria-hidden />
                  )}
                </AuthoringIconAction>
              ) : null}
              {canArchive ? (
                <AuthoringIconAction
                  write
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
    [busy, onArchive, onOpen, onToggleApproval],
  );

  if (org) {
    const emptyState = search
      ? { title: "No matching stations", description: "Try a different name, or clear the exam filter." }
      : { title: "No stations yet", description: canAuthor ? "Create one with New station, from a template or straight from a prompt." : READER_EMPTY_TEXT };
    if (stations.length === 0) {
      return (
        <div className={boardPadWide}>
          <h2 className="m-0 text-osce-body font-semibold !leading-[normal] text-ink">{emptyState.title}</h2>
          <p className={`m-0 ${boardMeta}`}>{emptyState.description}</p>
        </div>
      );
    }
    return (
      <div className={boardCardClipped}>
        <div className={boardHeadRowWide}>
          <span className="flex-[1_1_200px]">Station name</span>
          <span className="w-20">Exam</span>
          <span className="w-[200px]">Status</span>
          <span className="w-[90px]">Used by</span>
          <span className="w-[130px]">Created at</span>
          <span className="w-[150px]">Actions</span>
        </div>
        {stations.map((station) => (
          <div key={station.id} data-row className={boardRowWide}>
            <span className="flex-[1_1_200px]">
              <button type="button" onClick={() => onOpen(station)} className="p-0 text-left text-osce-accent hover:text-osce-accent-hover">
                {station.title}
              </button>
            </span>
            <span className="w-20">
              <BoardChip tone="info">{station.exam_code.toUpperCase()}</BoardChip>
            </span>
            <span className="w-[200px]">
              <StatusBadge status={station.status} />
              {station.status === "published" ? (
                <>
                  {" "}
                  <BoardChip tone={station.approved ? "ok" : "warn"}>{station.approved ? "Approved" : "Awaiting approval"}</BoardChip>
                </>
              ) : null}
            </span>
            <span className="w-[90px]">{usedByCell(station.used_by_count)}</span>
            <span className={`w-[130px] ${boardMeta}`}>{stationCreatedAtLabel(station, true)}</span>
            <span className="w-[150px]">
              {onToggleApproval && station.status === "published" ? (
                <button type="button" disabled={busy !== null} onClick={() => onToggleApproval(station)} className={boardButtonSmall}>
                  {station.approved ? "Withdraw approval" : "Approve"}
                </button>
              ) : null}
              {station.status === "published" && canAuthor ? (
                <button type="button" disabled={busy !== null} onClick={() => onArchive(station)} className={boardButtonSmall}>
                  {busy === `archive:${station.id}` ? "Archiving…" : "Archive"}
                </button>
              ) : null}
              <button type="button" onClick={() => onOpen(station)} className={boardButtonSmall}>
                Open versions ›
              </button>
            </span>
          </div>
        ))}
        {more.hasMore ? (
          <div className={cn(boardRowWide, "justify-center")}>
            <button type="button" disabled={more.loadingMore} onClick={more.loadMore} className={boardButtonSmall}>
              {more.loadingMore ? "Loading…" : "Load more"}
            </button>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <Table<Station>
      rows={stations}
      more={more}
      columns={columns}
      idField="id"
      empty={
        search
          ? { title: "No matching stations", description: "Try a different name, or clear the exam filter." }
          : !canAuthor
            ? { title: "No stations yet", description: READER_EMPTY_TEXT }
            : { title: "No stations yet", description: "Create one with New station, from a template or straight from a prompt." }
      }
    />
  );
}
