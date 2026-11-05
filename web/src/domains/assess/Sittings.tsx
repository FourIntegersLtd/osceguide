"use client";

import type { AssessWords } from "@/domains/assess/vocabulary";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AsyncBoundary,
  B2CHero,
  B2CPageHeader,
  Badge,
  ButtonLink,
  PlatformFilterSearch,
} from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useAsync, useCursorPages } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { humanise, plural } from "@/foundation/format";
import { useSurface } from "@/capabilities";
import { SittingFilterBar } from "@/domains/assess/SittingFilterBar";
import { listProgrammes, listSittings, type Sitting } from "@/domains/assess/api";
import {
  filtersActive,
  NO_SITTING_FILTERS,
  sittingFilterQuery,
  sittingNeedsCircuits,
  sittingRunning,
  sittingsEmptyDescription,
  sittingsScopeNote,
  type SittingFilters,
} from "@/domains/assess/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

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

const columnsFor = (hrefFor: (path: string) => string, words: AssessWords): Column<Sitting>[] => [
  {
    header: words.Sitting,
    key: "name",
    priority: "primary",
    render: (sitting: Sitting) => (
      <Link
        href={hrefFor(`/sittings/${sitting.id}`)}
        className={`${b2cTableCellText} font-medium text-osce-ink-900 hover:underline`}
      >
        {sitting.name}
        <span className="block text-osce-meta font-normal text-b2b-mid">
          {[
            sitting.programme_name,
            plural(sitting.candidate_count, "candidate"),
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
      </Link>
    ),
  },
  {
    header: "Kind",
    key: "mode" as keyof Sitting,
    render: (sitting: Sitting) => <span className={cell}>{sitting.mode === "exam" ? "Formal exam" : "Training"}</span>,
  },
  {
    header: "Exam",
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
      <Badge
        variant={sittingRunning(sitting.status) ? "success" : sittingNeedsCircuits(sitting) ? "warning" : "neutral"}
        dot
      >
        {sittingNeedsCircuits(sitting) ? "Needs circuits" : humanise(sitting.status)}
      </Badge>
    ),
  },
];

/** Scheduled examinations and training sessions. */
export function Sittings({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  // Status, mode, name search, programme and date are the server's (R-31), so they reach every page.
  const [filters, setFilters] = useState<SittingFilters>(NO_SITTING_FILTERS);
  const query = sittingFilterQuery(filters);
  const queryKey = JSON.stringify(query);
  const pages = useCursorPages<Sitting>(
    (cursor, signal) => listSittings(orgSlug, signal, { cursor }, query),
    [orgSlug, queryKey],
  );
  const programmes = useAsync((signal) => listProgrammes(orgSlug, signal), [orgSlug]);
  const columns = useMemo(() => columnsFor(hrefFor, w), [hrefFor, w]);
  // The box answers every keystroke; the server is asked once typing pauses.
  const [typed, setTyped] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setFilters((current) => ({ ...current, search: typed })), 300);
    return () => clearTimeout(timer);
  }, [typed]);
  const changeFilters = (next: SittingFilters) => {
    setFilters(next);
    if (next === NO_SITTING_FILTERS) setTyped("");
  };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title={w.Sittings}
        action={
          can(session, "schedule_sittings") ? (
            <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
              {w.scheduleSitting}
            </ButtonLink>
          ) : null
        }
      />

      <SittingFilterBar
        filters={filters}
        onChange={changeFilters}
        programmes={programmes.data?.items ?? []}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <PlatformFilterSearch
          value={typed}
          onChange={setTyped}
          placeholder={`Search by ${w.sitting} name`}
          aria-label={`Search ${w.sittings}`}
        />
      </div>

      <AsyncBoundary
        state={pages.state}
        isEmpty={(sittings) => sittings.length === 0 && !filtersActive(filters)}
        empty={{
          title: `No ${w.sittings} yet`,
          description: sittingsEmptyDescription(can(session, "schedule_sittings"), w),
          action: can(session, "schedule_sittings") ? (
            <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
              {w.scheduleSitting}
            </ButtonLink>
          ) : undefined,
        }}
      >
        {(sittings) => {
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
                      Open {w.sitting}
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
              {sittingsScopeNote(sittings.length, pages.hasMore) ? (
                <p className="text-osce-body text-b2b-mid">{sittingsScopeNote(sittings.length, pages.hasMore)}</p>
              ) : null}
              <Table<Sitting>
                rows={sittings}
                more={pages}
                themeType="b2b"
                columns={columns}
                idField="id"
                empty={{ title: `No ${w.sittings} match.`, description: "Clear a filter to see more." }}
              />
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
