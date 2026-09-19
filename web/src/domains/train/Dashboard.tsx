"use client";

import Link from "next/link";
import { LuArrowRight, LuCircleCheck, LuClock } from "react-icons/lu";
import { AsyncBoundary, Badge, ButtonLink, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readDashboard, type Dashboard as DashboardData } from "@/domains/train/api";

/**
 * Home for someone practising on their own.
 *
 * One request. The old consumer dashboard made seven — four grade endpoints, a
 * weekly trend and two marketplace lists — and joined them in the browser,
 * which is why it showed four different loading states and could half-fail.
 */
export function Dashboard() {
  const state = useAsync((signal) => readDashboard(signal), []);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Your practice" description="Where you left off, and what you have access to." />
      <AsyncBoundary state={state}>{(data) => <DashboardBody data={data} />}</AsyncBoundary>
    </div>
  );
}

function DashboardBody({ data }: { data: DashboardData }) {
  const { hrefFor } = useSurface();
  const entitlements = data.entitlements ?? [];
  const sets = data.sets ?? [];
  const progress = data.progress ?? [];
  const recent = data.recent_attempts ?? [];

  return (
    <div className="flex flex-col gap-6">
      <section className="grid gap-3 sm:grid-cols-3">
        {progress.map((exam) => (
          <Card key={exam.exam_code}>
            <p className="text-xs uppercase tracking-wide text-ink-subtle">
              {exam.exam_code.toUpperCase()}
            </p>
            <p className="mt-1 text-2xl font-semibold text-ink">{exam.attempts}</p>
            <p className="text-sm text-ink-muted">
              {exam.evaluated} marked
              {exam.last_attempt_at
                ? ` · last ${new Date(exam.last_attempt_at).toLocaleDateString()}`
                : ""}
            </p>
          </Card>
        ))}
        {progress.length === 0 && (
          <Card className="sm:col-span-3">
            <p className="text-sm text-ink-muted">
              You have not attempted a station yet. Pick one from the library to begin.
            </p>
            <ButtonLink className="mt-3" href={hrefFor("/stations")}>
              Browse stations
            </ButtonLink>
          </Card>
        )}
      </section>

      <Card
        title="Your mocks"
        description="Sets of stations you have put together."
        actions={
          <Link
            href={hrefFor("/mocks")}
            className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
          >
            All mocks <LuArrowRight className="h-4 w-4" aria-hidden />
          </Link>
        }
      >
        {sets.length === 0 ? (
          <p className="text-sm text-ink-muted">
            No mocks yet. Build one from the station library and work through it.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {sets.slice(0, 4).map((set) => (
              <li key={set.id}>
                <Link
                  href={hrefFor(`/mocks/${set.id}`)}
                  className="flex items-center justify-between gap-3 rounded-control border border-border px-3 py-2.5 hover:border-border-strong"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-ink">{set.name}</span>
                    <span className="text-xs text-ink-subtle">
                      {set.attempted_entries} of {set.total_entries} attempted
                    </span>
                  </span>
                  {set.locked ? (
                    <Badge tone="warning">Locked</Badge>
                  ) : (
                    <Badge tone="accent">{set.exam_code.toUpperCase()}</Badge>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Your access">
          {entitlements.length === 0 ? (
            <p className="text-sm text-ink-muted">You have no active access.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {entitlements.map((entitlement) => (
                <li
                  key={`${entitlement.exam_code}-${entitlement.source}`}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span className="text-ink">{entitlement.exam_code.toUpperCase()}</span>
                  <span className="flex items-center gap-2 text-ink-muted">
                    <span className="text-xs capitalize">{entitlement.source}</span>
                    {entitlement.live ? (
                      <Badge tone="success">
                        <LuCircleCheck className="mr-1 h-3 w-3" aria-hidden /> Active
                      </Badge>
                    ) : (
                      <Badge tone="neutral">Expired</Badge>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent attempts">
          {recent.length === 0 ? (
            <p className="text-sm text-ink-muted">Nothing yet.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {recent.slice(0, 6).map((attempt) => (
                <li key={attempt.id}>
                  <Link
                    href={hrefFor(`/attempts/${attempt.id}`)}
                    className="flex items-center justify-between gap-3 text-sm hover:underline"
                  >
                    <span className="text-ink">{attempt.exam_code.toUpperCase()}</span>
                    <span className="flex items-center gap-2 text-ink-muted">
                      {attempt.has_result ? (
                        <Badge tone="success">Marked</Badge>
                      ) : (
                        <Badge tone="neutral">
                          <LuClock className="mr-1 h-3 w-3" aria-hidden /> {attempt.status}
                        </Badge>
                      )}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
