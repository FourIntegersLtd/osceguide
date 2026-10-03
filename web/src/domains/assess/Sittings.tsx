"use client";

import { useState } from "react";
import { LuCalendarDays } from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  B2CSegmentedTabs,
  Badge,
  ButtonLink,
  PlatformFilterSearch,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
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

function matches(sitting: Sitting, term: string): boolean {
  if (!term) return true;
  return `${sitting.name} ${sitting.programme_name ?? ""}`.toLowerCase().includes(term);
}

/** Scheduled examinations and training sessions. */
export function Sittings({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => listSittings(orgSlug, signal), [orgSlug]);
  const [filter, setFilter] = useState<ModeFilter>("all");
  const [search, setSearch] = useState("");

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Sittings"
        subtitle="Examinations and training sessions your organisation runs."
        action={
          <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
            Schedule a sitting
          </ButtonLink>
        }
      />

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No sittings yet",
          description: "Schedule your first one to get started.",
        }}
      >
        {(page) => {
          const term = search.trim().toLowerCase();
          const rows = page.items.filter(
            (sitting) => (filter === "all" || sitting.mode === filter) && matches(sitting, term),
          );
          const next = nextUp(page.items);
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
              {rows.length === 0 ? (
                <p className="text-osce-body text-b2b-mid">No sittings match.</p>
              ) : null}
              <B2CGroupedSection eyebrow="Sittings">
                {rows.map((sitting) => (
                  <B2CGroupedRowLink
                    key={sitting.id}
                    href={hrefFor(`/sittings/${sitting.id}`)}
                    icon={LuCalendarDays}
                    title={sitting.name}
                    meta={[
                      sitting.mode,
                      sitting.programme_name,
                      `${sitting.candidate_count} ${sitting.candidate_count === 1 ? "candidate" : "candidates"}`,
                      sitting.scheduled_for
                        ? new Date(sitting.scheduled_for).toLocaleString()
                        : "Not scheduled",
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                    trailing={
                      <Badge variant={RUNNING.has(sitting.status) ? "success" : "neutral"} dot>
                        {sitting.status}
                      </Badge>
                    }
                  />
                ))}
              </B2CGroupedSection>
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
