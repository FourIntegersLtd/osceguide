"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  AsyncBoundary,
  B2CHero,
  B2CPageHeader,
  B2CSegmentedTabs,
  Badge,
  ButtonLink,
  PlatformFilterSearch,
} from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useAsync, useCursorPages } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { listProgrammes, listSittings, type Sitting } from "@/domains/assess/api";
import {
  filtersActive,
  NO_SITTING_FILTERS,
  sittingFilterQuery,
  sittingRunning,
  sittingsEmptyDescription,
  sittingsScopeNote,
  type SittingFilters,
} from "@/domains/assess/support";

type ModeFilter = "all" | "exam" | "training";

/** The sitting running now, else the soonest one still to come; finished ones are never next. */
export function nextUp(sittings: Sitting[], now: number = Date.now()): Sitting | null {
  const open = sittings.filter((sitting) => sitting.status !== "completed");
  const running = open.find((sitting) => sittingRunning(sitting.status));
  if (running) return running;
  const upcoming = open
    .filter((sitting) => sitting.scheduled_for && new Date(sitting.scheduled_for).getTime() >= now)
    .sort(
      (a, b) =>
        new Date(a.scheduled_for ?? 0).getTime() - new Date(b.scheduled_for ?? 0).getTime(),
    );
  return upcoming[0] ?? null;
}

const cell = `${b2cTableCellText} text-b2b-graphite`;

const columnsFor = (hrefFor: (path: string) => string): Column<Sitting>[] => [
  {
    header: "Sitting",
    key: "name",
    priority: "primary",
    render: (sitting: Sitting) => (
      <Link
        href={hrefFor(`/sittings/${sitting.id}`)}
        className={`${b2cTableCellText} font-medium text-osce-ink-900 hover:underline`}
      >
        {sitting.name}
      </Link>
    ),
  },
  {
    header: "Mode",
    key: "mode" as keyof Sitting,
    render: (sitting: Sitting) => <span className={`${cell} capitalize`}>{sitting.mode}</span>,
  },
  {
    header: "Programme",
    key: "programme_name" as keyof Sitting,
    render: (sitting: Sitting) => <span className={cell}>{sitting.programme_name ?? ""}</span>,
  },
  {
    header: "Scheduled for",
    key: "scheduled_for" as keyof Sitting,
    render: (sitting: Sitting) => (
      <span className={cell}>
        {sitting.scheduled_for ? new Date(sitting.scheduled_for).toLocaleDateString() : "Not scheduled"}
      </span>
    ),
  },
  {
    header: "Status",
    key: "status" as keyof Sitting,
    render: (sitting: Sitting) => (
      <Badge variant={sittingRunning(sitting.status) ? "success" : "neutral"} dot>
        {sitting.status.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}
      </Badge>
    ),
  },
];

function matches(sitting: Sitting, term: string): boolean {
  if (!term) return true;
  return `${sitting.name} ${sitting.programme_name ?? ""}`.toLowerCase().includes(term);
}

/** Scheduled examinations and training sessions. */
export function Sittings({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const { session } = useSession();
  // Status, programme and date are the server's (R-31), so they reach every page. The endpoint
  // takes no search, so the mode tabs and the search box narrow what has been loaded so far.
  const [filters, setFilters] = useState<SittingFilters>(NO_SITTING_FILTERS);
  const query = sittingFilterQuery(filters);
  const queryKey = JSON.stringify(query);
  const pages = useCursorPages<Sitting>(
    (cursor, signal) => listSittings(orgSlug, signal, { cursor }, query),
    [orgSlug, queryKey],
  );
  const programmes = useAsync((signal) => listProgrammes(orgSlug, signal), [orgSlug]);
  const columns = useMemo(() => columnsFor(hrefFor), [hrefFor]);
  const [filter, setFilter] = useState<ModeFilter>("all");
  const [search, setSearch] = useState("");

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Sittings"
        action={
          can(session, "schedule_sittings") ? (
            <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
              Schedule a sitting
            </ButtonLink>
          ) : null
        }
      />

      <SittingFilterBar
        filters={filters}
        onChange={setFilters}
        programmes={programmes.data?.items ?? []}
      />

      <AsyncBoundary
        state={pages.state}
        isEmpty={(sittings) => sittings.length === 0 && !filtersActive(filters)}
        empty={{
          title: "No sittings yet",
          description: sittingsEmptyDescription(can(session, "schedule_sittings")),
        }}
      >
        {(sittings) => {
          const term = search.trim().toLowerCase();
          const rows = sittings.filter(
            (sitting) => (filter === "all" || sitting.mode === filter) && matches(sitting, term),
          );
          const next = nextUp(sittings);
          return (
            <div className="flex flex-col gap-4">
              {next ? (
                <B2CHero
                  eyebrow="Next up"
                  title={
                    sittingRunning(next.status) ? `${next.name} is running now` : next.name
                  }
                  action={
                    <ButtonLink
                      href={hrefFor(`/sittings/${next.id}`)}
                      themeType="b2b"
                      variant="secondary"
                    >
                      Open sitting
                    </ButtonLink>
                  }
                >
                  {[
                    next.programme_name,
                    next.scheduled_for ? new Date(next.scheduled_for).toLocaleString() : null,
                    `${next.candidate_count} ${next.candidate_count === 1 ? "candidate" : "candidates"}`,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </B2CHero>
              ) : null}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <B2CSegmentedTabs<ModeFilter>
                  aria-label="Filter by mode"
                  compact
                  value={filter}
                  onChange={setFilter}
                  items={[
                    { id: "all", label: "All" },
                    { id: "exam", label: "Exam" },
                    { id: "training", label: "Training" },
                  ]}
                />
                <PlatformFilterSearch
                  value={search}
                  onChange={setSearch}
                  placeholder="Search sittings"
                  aria-label="Search sittings"
                />
              </div>
              {sittingsScopeNote(sittings.length, pages.hasMore) ? (
                <p className="text-osce-body text-b2b-mid">{sittingsScopeNote(sittings.length, pages.hasMore)}</p>
              ) : null}
              <Table<Sitting>
                rows={rows}
                more={pages}
                themeType="b2b"
                columns={columns}
                idField="id"
                empty={{ title: "No sittings match." }}
              />
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

const FIELD =
  "rounded-control border border-b2b-border bg-b2b-surface px-3 py-2 text-osce-meta text-b2b-headline";

const STATUSES = ["scheduled", "in_progress", "completed", "cancelled"];

/** Status, programme and date, applied by the server so they cover every page. */
function SittingFilterBar({
  filters,
  onChange,
  programmes,
}: {
  filters: SittingFilters;
  onChange: (next: SittingFilters) => void;
  programmes: { id: string; exam_name: string }[];
}) {
  const set = (patch: Partial<SittingFilters>) => onChange({ ...filters, ...patch });
  return (
    <div className="flex flex-wrap items-end gap-3" role="group" aria-label="Filter sittings">
      <label className="flex flex-col gap-1 text-osce-meta text-b2b-mid">
        Status
        <select className={FIELD} value={filters.status} onChange={(e) => set({ status: e.target.value })}>
          <option value="">Any status</option>
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {status.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-osce-meta text-b2b-mid">
        Programme
        <select
          className={FIELD}
          value={filters.programmeId}
          onChange={(e) => set({ programmeId: e.target.value })}
        >
          <option value="">Any programme</option>
          {programmes.map((programme) => (
            <option key={programme.id} value={programme.id}>
              {programme.exam_name}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-osce-meta text-b2b-mid">
        From
        <input type="date" className={FIELD} value={filters.from} onChange={(e) => set({ from: e.target.value })} />
      </label>
      <label className="flex flex-col gap-1 text-osce-meta text-b2b-mid">
        To
        <input type="date" className={FIELD} value={filters.to} onChange={(e) => set({ to: e.target.value })} />
      </label>
      {filtersActive(filters) ? (
        <button type="button" className="text-osce-meta underline" onClick={() => onChange(NO_SITTING_FILTERS)}>
          Clear filters
        </button>
      ) : null}
    </div>
  );
}
