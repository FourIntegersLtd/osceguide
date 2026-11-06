"use client";

import type { AssessWords } from "@/domains/assess/vocabulary";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AsyncBoundary, b2bTokens as t } from "@/foundation/ui";
import { useAsync, useCursorPages } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { SittingFilterBar } from "@/domains/assess/SittingFilterBar";
import {
  listProgrammes,
  listSittings,
  type Sitting,
} from "@/domains/assess/api";
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
import { sittingTally } from "@/domains/assess/dashboard/support";
import { boardCard, boardHeadRow, boardPad, boardRow, boardTab, boardTabs, boardChip, boardButtonSmall , boardBtn } from "@/foundation/ui/boardKit";
import {
  sittingChipTone,
  sittingWhen,
  sittingWhenAt,
} from "@/domains/assess/sittingWords";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/** The sitting running now, else the soonest one still to come; finished ones are never next. */
export function nextUp(
  sittings: Sitting[],
  now: number = Date.now(),
): Sitting | null {
  const open = sittings.filter((sitting) => sitting.status !== "completed");
  const running = open.find((sitting) => sittingRunning(sitting.status));
  if (running) return running;
  const upcoming = open
    .filter(
      (sitting) =>
        sitting.scheduled_for &&
        new Date(sitting.scheduled_for).getTime() >= now,
    )
    .sort(
      (a, b) =>
        new Date(a.scheduled_for ?? 0).getTime() -
        new Date(b.scheduled_for ?? 0).getTime(),
    );
  return upcoming[0] ?? null;
}

const TABS: [string, string][] = [
  ["", "All"],
  ["scheduled", "Scheduled"],
  ["in_progress", "Running"],
  ["completed", "Finished"],
  ["cancelled", "Cancelled"],
];

const statusWords: Record<string, string> = {
  scheduled: "Scheduled",
  in_progress: "Running",
  completed: "Finished",
  cancelled: "Cancelled",
};

/** Scheduled examinations and training sessions, drawn to docs/institution-overhaul/boards/Sittings.dc.html. */
export function Sittings({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  // Status, mode, name search, programme and date are the server's (R-31), so they reach every page.
  // `?exam=` is a programme id: an exam's page links here with it, so the list opens already narrowed.
  const examFilter = useSearchParams().get("exam") ?? "";
  const [filters, setFilters] = useState<SittingFilters>({
    ...NO_SITTING_FILTERS,
    programmeId: examFilter,
  });
  const query = sittingFilterQuery(filters);
  const queryKey = JSON.stringify(query);
  const pages = useCursorPages<Sitting>(
    (cursor, signal) => listSittings(orgSlug, signal, { cursor }, query),
    [orgSlug, queryKey],
  );
  const programmes = useAsync(
    (signal) => listProgrammes(orgSlug, signal),
    [orgSlug],
  );
  // The box answers every keystroke; the server is asked once typing pauses.
  const [typed, setTyped] = useState("");
  useEffect(() => {
    const timer = setTimeout(
      () => setFilters((current) => ({ ...current, search: typed })),
      300,
    );
    return () => clearTimeout(timer);
  }, [typed]);
  const changeFilters = (next: SittingFilters) => {
    setFilters(next);
    if (next === NO_SITTING_FILTERS) setTyped("");
  };
  const canSchedule = can(session, "schedule_sittings");
  const schedule = canSchedule ? (
    <Link href={hrefFor("/sittings/new")} className={boardBtn("primary")}>
      {w.scheduleSitting}
    </Link>
  ) : null;

  const loaded = pages.state.data;
  const hasAny = loaded === null || loaded.length > 0 || filtersActive(filters);
  const next = loaded ? nextUp(loaded) : null;
  const hero = next ? (
    <div
      className={`flex flex-wrap items-center justify-between gap-5 p-6 rounded-panel border border-assess-select-border bg-assess-hero-live-bg`}
    >
      <div>
        <div className={t.assessEyebrow}>Next up</div>
        <h2 className="mt-1 text-xl font-semibold leading-[1.3]">
          {sittingRunning(next.status)
            ? `${next.name} is running now`
            : next.name}
        </h2>
        <div className={t.assessMeta}>
          {[
            next.programme_name,
            next.scheduled_for ? sittingWhenAt(next.scheduled_for) : null,
            `${next.candidate_count} ${next.candidate_count === 1 ? "candidate" : "candidates"}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </div>
      </div>
      <Link
        href={hrefFor(`/sittings/${next.id}`)}
        className={boardBtn("primary")}
      >
        Open {w.sitting}
      </Link>
    </div>
  ) : null;

  return (
    <section aria-label={w.Sittings} className={t.assessPage}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={t.assessEyebrow}>Run</div>
          <h1 className={t.assessTitle}>{w.Sittings}</h1>
          <p className={t.assessDesc}>
            {`${w.hiring ? "An" : "A"} ${w.sitting} is one occasion, such as the March mock. Its circuits are built for you when you schedule it.`}
          </p>
        </div>
        {schedule ? (
          <div className="flex flex-wrap items-center gap-2.5">{schedule}</div>
        ) : null}
      </div>

      {hasAny ? hero : null}
      {hasAny ? (
        <>
          <div role="tablist" className={boardTabs}>
            {TABS.map(([status, label]) => (
              <button
                key={label}
                type="button"
                role="tab"
                aria-selected={filters.status === status}
                className={boardTab(filters.status === status)}
                onClick={() => changeFilters({ ...filters, status })}
              >
                {label}
              </button>
            ))}
          </div>
          <SittingFilterBar
            filters={filters}
            onChange={changeFilters}
            programmes={programmes.data?.items ?? []}
            search={typed}
            onSearch={setTyped}
          />
        </>
      ) : null}

      <AsyncBoundary state={pages.state}>
        {(sittings) =>
          sittings.length === 0 && !filtersActive(filters) ? (
            <div className={boardPad}>
              <h2 className="text-base font-semibold leading-normal">{`No ${w.sittings} yet`}</h2>
              <p className={`m-0 ${t.assessMeta}`}>
                {sittingsEmptyDescription(canSchedule, w)}
              </p>
              {schedule ? (
                <div className="flex self-start">{schedule}</div>
              ) : null}
            </div>
          ) : (
            <>
              {sittingsScopeNote(sittings.length, pages.hasMore) ? (
                <p className={t.assessMeta}>
                  {sittingsScopeNote(sittings.length, pages.hasMore)}
                </p>
              ) : null}
              <SittingRows
                sittings={sittings}
                pages={pages}
                hrefFor={hrefFor}
                words={w}
              />
            </>
          )
        }
      </AsyncBoundary>
    </section>
  );
}

function SittingRows({
  sittings,
  pages,
  hrefFor,
  words,
}: {
  sittings: Sitting[];
  pages: {
    hasMore: boolean;
    loadingMore: boolean;
    moreError: Error | null;
    loadMore: () => void;
  };
  hrefFor: (path: string) => string;
  words: AssessWords;
}) {
  if (sittings.length === 0) {
    return (
      <div className={boardPad}>
        <h2 className="text-base font-semibold leading-normal">{`No ${words.sittings} match.`}</h2>
        <p className={`m-0 ${t.assessMeta}`}>Clear a filter to see more.</p>
      </div>
    );
  }
  return (
    <div className={`${boardCard} overflow-hidden`}>
      <div className={boardHeadRow}>
        <span className="flex-[1_1_240px]">{words.Sitting}</span>
        <span className="w-[110px]">Kind</span>
        <span className="w-[140px]">Exam</span>
        <span className="w-[110px]">Date</span>
        <span className="w-[120px]">Status</span>
      </div>
      {sittings.map((sitting) => {
        const needs = sittingNeedsCircuits(sitting);
        return (
          <Link
            key={sitting.id}
            href={hrefFor(`/sittings/${sitting.id}`)}
            className={`${boardRow} hover:bg-osce-surface-inset`}
          >
            <div className="flex-[1_1_240px]">
              <div className="font-medium">{sitting.name}</div>
              <div className={t.assessMeta}>
                {[sitting.programme_name, sittingTally(sitting, words)]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
            </div>
            <span className={`w-[110px] ${t.assessMeta}`}>
              {sitting.mode === "exam" ? "Formal exam" : "Training"}
            </span>
            <span className={`w-[140px] ${t.assessMeta}`}>
              {sitting.programme_name ?? ""}
            </span>
            <span className="w-[110px]">
              {sittingWhen(sitting.scheduled_for)}
            </span>
            <span className="w-[120px]">
              <span
                className={boardChip(sittingChipTone(sitting.status, needs))}
              >
                {needs
                  ? "Needs circuits"
                  : (statusWords[sitting.status] ?? sitting.status)}
              </span>
            </span>
          </Link>
        );
      })}
      {pages.hasMore || pages.moreError ? (
        <div className={`${boardRow} justify-center`}>
          {pages.moreError ? (
            <span className={t.assessMeta}>
              Could not load more: {pages.moreError.message}
            </span>
          ) : null}
          {pages.hasMore ? (
            <button
              type="button"
              className={boardButtonSmall}
              disabled={pages.loadingMore}
              onClick={pages.loadMore}
            >
              {pages.loadingMore
                ? "Loading…"
                : pages.moreError
                  ? "Try again"
                  : "Load more"}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
