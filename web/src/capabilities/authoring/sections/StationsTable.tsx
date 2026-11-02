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
import { cn } from "@/foundation/ui/cn";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";

function stationCreatedAtLabel(station: Station): string {
  const raw = station.content?.created_at;
  const iso = typeof raw === "string" ? raw : null;
  if (!iso) return "-";
  const normalized = /[zZ]$/.test(iso) || /[+-]\d{2}/.test(iso) ? iso : `${iso}Z`;
  const date = new Date(normalized);
  if (!Number.isFinite(date.getTime())) return "-";
  return date.toLocaleString("en-GB");
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
