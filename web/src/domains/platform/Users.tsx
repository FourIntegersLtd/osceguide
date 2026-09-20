"use client";

import { useState } from "react";
import type { IconType } from "react-icons";
import { LuCreditCard, LuUserRound, LuUsers } from "react-icons/lu";
import { AsyncBoundary, Card } from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listPlans } from "@/capabilities/account/api";
import {
  readDirectorySummary,
  type DirectoryFilters as Filters,
  type DirectorySummary,
} from "@/domains/platform/api";
import { DirectoryFilters } from "@/domains/platform/users/DirectoryFilters";
import { UserGroup } from "@/domains/platform/users/UserGroup";
import { directoryListingTotal, groupTitle } from "@/domains/platform/users/vocabulary";

const NONE: Filters = { q: null, examCode: null, status: null, access: null, planCode: null };

/**
 * The account directory: everyone, grouped by exam, with the retiring B2C
 * admin's columns and filters.
 *
 * That console had a page per exam because each exam was its own database.
 * Here an account is one row whatever it holds, so the exams are groups on
 * one screen, each paging on its own, and the counts across the top come
 * from one summary call rather than from having loaded everybody.
 */
export function Users() {
  const { hrefFor } = useSurface();
  const [filters, setFilters] = useState<Filters>(NONE);
  const [term, setTerm] = useState("");
  const summary = useAsync((signal) => readDirectorySummary(signal), []);
  const plans = useAsync(
    async (signal) => (await listPlans(signal)).items.map((plan) => plan.code),
    [],
  );

  const clear = () => {
    setTerm("");
    setFilters(NONE);
  };

  return (
    <div className="flex flex-col gap-8">
      <PlatformPageHeader
        title="Users"
        description="Everyone with an account, grouped by the exam they are here for."
        icon={LuUsers}
      />

      <AsyncBoundary state={summary}>
        {(counts) => (
          <>
            <SummaryStrip summary={counts} />
            <DirectoryFilters
              exams={counts.exams}
              plans={plans.data ?? []}
              filters={filters}
              term={term}
              onTerm={setTerm}
              onChange={setFilters}
            />
            <Groups summary={counts} filters={filters} hrefFor={hrefFor} onClear={clear} />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

function Groups({
  summary,
  filters,
  hrefFor,
  onClear,
}: {
  summary: DirectorySummary;
  filters: Filters;
  hrefFor: (path: string) => string;
  onClear: () => void;
}) {
  if (filters.examCode) {
    const exam = summary.exams.find((entry) => entry.code === filters.examCode);
    return (
      <UserGroup
        title={exam ? groupTitle(exam.code, exam.name, exam.users) : filters.examCode.toUpperCase()}
        filters={filters}
        hrefFor={hrefFor}
        totalCount={directoryListingTotal(summary, filters)}
        onClear={onClear}
      />
    );
  }
  // Busiest exam first, and the exams nobody is on yet as one line rather
  // than a run of empty cards above the people who are actually here.
  const populated = summary.exams.filter((exam) => exam.users > 0).sort((a, b) => b.users - a.users);
  const empty = summary.exams.filter((exam) => exam.users === 0);
  return (
    <>
      {populated.map((exam) => (
        <UserGroup
          key={exam.code}
          title={groupTitle(exam.code, exam.name, exam.users)}
          description={`${exam.paid} paid · ${exam.trial} on trial · ${exam.not_started} not started`}
          filters={{ ...filters, examCode: exam.code }}
          hrefFor={hrefFor}
          totalCount={directoryListingTotal(summary, { ...filters, examCode: exam.code })}
          onClear={onClear}
        />
      ))}
      <UserGroup
        title={`No exam chosen · ${summary.unassigned}`}
        description="Accounts naming no exam and holding no live access. Staff accounts sit here too."
        filters={{ ...filters, examCode: null, unassigned: true }}
        hrefFor={hrefFor}
        totalCount={directoryListingTotal(summary, { ...filters, examCode: null, unassigned: true })}
        onClear={onClear}
      />
      {empty.length > 0 ? (
        <Card padding="md">
          <p className="text-sm text-ink-muted">
            Nobody yet on {empty.map((exam) => exam.name || exam.code.toUpperCase()).join(", ")}.
          </p>
        </Card>
      ) : null}
    </>
  );
}

function SummaryStrip({ summary }: { summary: DirectorySummary }) {
  const paid = summary.exams.reduce((sum, exam) => sum + exam.paid, 0);
  const trial = summary.exams.reduce((sum, exam) => sum + exam.trial, 0);
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Stat label="Accounts" value={summary.total} icon={LuUsers} />
      <Stat label="Paid" value={paid} icon={LuCreditCard} />
      <Stat label="On trial" value={trial} icon={LuUserRound} />
    </div>
  );
}

function Stat({ label, value, icon: Icon }: { label: string; value: number; icon: IconType }) {
  return (
    <Card padding="md">
      <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-ink-subtle">
        <Icon className="h-3.5 w-3.5" aria-hidden /> {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </Card>
  );
}
