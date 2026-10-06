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
import { useCursorPages } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { listSittings, type Sitting } from "@/domains/assess/api";

type ModeFilter = "all" | "exam" | "training";

const RUNNING = new Set(["in_progress", "live"]);

/** The sitting running now, else the soonest one still to come; finished ones are never next. */
export function nextUp(sittings: Sitting[], now: number = Date.now()): Sitting | null {
  const open = sittings.filter((sitting) => sitting.status !== "completed");
  const running = open.find((sitting) => RUNNING.has(sitting.status));
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
      <Badge variant={RUNNING.has(sitting.status) ? "success" : "neutral"} dot>
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
  // A server page at a time. The endpoint takes no search, so the mode filter
  // and the search box narrow what has been loaded so far.
  const pages = useCursorPages<Sitting>(
    (cursor, signal) => listSittings(orgSlug, signal, { cursor }),
    [orgSlug],
  );
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

      <AsyncBoundary
        state={pages.state}
        isEmpty={(sittings) => sittings.length === 0}
        empty={{
          title: "No sittings yet",
          description: "Schedule your first one to get started.",
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
                    RUNNING.has(next.status) ? `${next.name} is running now` : next.name
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
